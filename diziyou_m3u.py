#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Diziyou M3U Oluşturucu - Güncellenmiş Sürüm
"""
import requests
import random
import time
import re
from bs4 import BeautifulSoup
from datetime import datetime
import sys

USER_AGENTS = [
    'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
    'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36',
]

def get_random_headers(referer=None):
    headers = {
        'User-Agent': random.choice(USER_AGENTS),
        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
    }
    if referer:
        headers['Referer'] = referer
    return headers

def get_base_url():
    primary_url = "https://www.diziyou.one/"
    backup_url = "https://www.diziyou.io/"
    
    headers = get_random_headers()
    try:
        resp = requests.head(primary_url, headers=headers, timeout=10, allow_redirects=True)
        if resp.status_code < 400:
            return primary_url.rstrip('/')
    except:
        pass
    
    try:
        resp = requests.head(backup_url, headers=headers, timeout=10, allow_redirects=False)
        if 300 <= resp.status_code < 400:
            location = resp.headers.get('Location', '')
            if location:
                return location.rstrip('/')
    except:
        pass
    
    return primary_url.rstrip('/')

def get_all_series_links(base_url):
    series_list = []
    page = 1
    
    while True:
        url = f"{base_url}/dizi-arsivi" if page == 1 else f"{base_url}/dizi-arsivi/page/{page}"
        headers = get_random_headers(base_url)
        
        try:
            print(f"📄 Sayfa {page} çekiliyor...")
            resp = requests.get(url, headers=headers, timeout=20)
            resp.raise_for_status()
            soup = BeautifulSoup(resp.content, 'html.parser')
            
            page_series = []
            links = soup.find_all('a', href=True, title=True)
            
            for link in links:
                href = link['href']
                title = link['title'].strip()
                
                if (href.startswith(base_url) and 
                    not href.endswith('/dizi-arsivi') and
                    'page/' not in href and
                    title and len(title) > 2):
                    
                    page_series.append({
                        'name': title,
                        'url': href,
                        'poster': None
                    })
            
            if not page_series:
                break
                
            series_list.extend(page_series)
            print(f"✅ {len(page_series)} dizi eklendi")
            
            # Her dizi için kapak resmini al
            for series in page_series:
                series['poster'] = get_series_poster(series['url'], base_url)
            
            page += 1
            time.sleep(2)
            
        except Exception as e:
            print(f"❌ Sayfa {page} hatası: {e}")
            break
    
    print(f"\n🎬 Toplam {len(series_list)} dizi bulundu")
    return series_list[:30]  # Test için 30 dizi (hepsi için [:30] kaldır)

def get_series_poster(series_url, base_url):
    """Dizi kapak resmini al"""
    headers = get_random_headers(base_url)
    try:
        resp = requests.get(series_url, headers=headers, timeout=15)
        soup = BeautifulSoup(resp.content, 'html.parser')
        
        # Kapak resmini bul
        poster_div = soup.find('div', class_='category_image')
        if poster_div:
            img = poster_div.find('img', src=True)
            if img and 'src' in img.attrs:
                return img['src']
        
        # Alternatif arama
        img = soup.find('img', class_='poster')
        if img and 'src' in img.attrs:
            return img['src']
            
    except:
        pass
    
    return "https://via.placeholder.com/300x450/2d2d2d/ffffff?text=No+Poster"

def scrape_series_details(series_url, series_name, poster_url, base_url):
    """Dizi detaylarını çek"""
    headers = get_random_headers(base_url)
    
    try:
        resp = requests.get(series_url, headers=headers, timeout=20)
        soup = BeautifulSoup(resp.content, 'html.parser')
        
        episodes = []
        episodes_container = soup.find('div', id='scrollbar-container')
        
        if episodes_container:
            episode_links = episodes_container.find_all('a', href=True)
            
            for ep_link in episode_links:
                ep_url = ep_link['href']
                
                baslik_div = ep_link.find('div', class_='baslik')
                tarih_div = ep_link.find('div', class_='tarih')
                bolumismi_div = ep_link.find('div', class_='bolumismi')
                
                if baslik_div:
                    raw_title = baslik_div.text.strip()
                    
                    # Sezon ve bölüm numaralarını çıkar
                    season_num = 1
                    episode_num = 1
                    
                    season_match = re.search(r'(\d+)\s*[.]?\s*[Ss]ezon', raw_title)
                    episode_match = re.search(r'(\d+)\s*[.]?\s*[Bb]ölüm', raw_title)
                    
                    if season_match:
                        season_num = int(season_match.group(1))
                    if episode_match:
                        episode_num = int(episode_match.group(1))
                    
                    episode_date = tarih_div.text.strip() if tarih_div else ""
                    episode_name = bolumismi_div.text.strip('() ') if bolumismi_div else ""
                    
                    # TVG formatında bölüm ismi
                    tvg_name = f"{series_name} S{season_num:02d}E{episode_num:02d}"
                    if episode_name:
                        tvg_name += f" - {episode_name}"
                    
                    episodes.append({
                        'url': ep_url,
                        'tvg_name': tvg_name,
                        'raw_title': raw_title,
                        'season': season_num,
                        'episode': episode_num,
                        'date': episode_date,
                        'episode_name': episode_name
                    })
        
        return {
            'name': series_name,
            'url': series_url,
            'poster': poster_url,
            'episodes': episodes
        }
        
    except Exception as e:
        print(f"  ❌ {series_name} hatası: {e}")
        return {
            'name': series_name,
            'url': series_url,
            'poster': poster_url,
            'episodes': []
        }

def generate_m3u(all_series_data, base_url):
    """Standart M3U formatında dosya oluştur"""
    
    m3u_lines = [
        '#EXTM3U',
        f'# Generated: {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}',
        f'# Base URL: {base_url}',
        ''
    ]
    
    total_episodes = 0
    
    for series in all_series_data:
        if not series['episodes']:
            continue
            
        print(f"📺 {series['name']}: {len(series['episodes'])} bölüm")
        
        for episode in series['episodes']:
            # EXTINF satırı - TVG formatında
            duration = -1  # Bilinmiyor
            tvg_id = f"{series['name'].replace(' ', '_')}_S{episode['season']:02d}E{episode['episode']:02d}"
            
            extinf_line = f'#EXTINF:{duration} tvg-id="{tvg_id}" tvg-name="{episode["tvg_name"]}" tvg-logo="{series["poster"]}" group-title="{series["name"]}",{episode["tvg_name"]}'
            
            m3u_lines.append(extinf_line)
            m3u_lines.append(episode['url'])
            total_episodes += 1
    
    print(f"\n✅ Toplam {total_episodes} bölüm M3U'ya eklendi!")
    return '\n'.join(m3u_lines)

def main():
    print("="*60)
    print("DİZİYOU M3U OLUŞTURUCU - TVG FORMAT")
    print("="*60)
    
    # 1. Ana URL
    base_url = get_base_url()
    print(f"🌐 Site: {base_url}")
    
    # 2. Dizi linkleri ve posterler
    series_links = get_all_series_links(base_url)
    
    if not series_links:
        print("\n❌ Hiç dizi bulunamadı!")
        return
    
    # 3. Her dizi için detaylar
    print(f"\n{'='*50}")
    print("Bölüm bilgileri çekiliyor...")
    
    all_series_data = []
    for i, series in enumerate(series_links, 1):
        print(f"\n[{i}/{len(series_links)}] {series['name']}")
        series_data = scrape_series_details(
            series['url'], 
            series['name'], 
            series['poster'], 
            base_url
        )
        all_series_data.append(series_data)
        time.sleep(1)
    
    # 4. M3U oluştur
    m3u_content = generate_m3u(all_series_data, base_url)
    
    # 5. Dosyaya yaz
    try:
        with open("diziyou.m3u", "w", encoding="utf-8") as f:
            f.write(m3u_content)
        
        # Kontrol
        with open("diziyou.m3u", "r", encoding="utf-8") as f:
            lines = f.readlines()
        
        print(f"\n✅ M3U dosyası oluşturuldu!")
        print(f"📊 Dosya boyutu: {len(m3u_content)} karakter")
        print(f"📄 Satır sayısı: {len(lines)}")
        print(f"💾 Kaydedildi: diziyou.m3u")
        
        # Örnek göster
        print("\n📋 İlk 3 giriş:")
        print("-"*40)
        for line in m3u_content.split('\n')[:7]:
            print(line)
        print("-"*40)
        
    except Exception as e:
        print(f"\n❌ Dosya yazma hatası: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()
