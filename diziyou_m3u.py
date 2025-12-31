#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Diziyou M3U Oluşturucu - OPTİMİZE & PARALEL TAM SÜRÜM
"""
import requests
import random
import time
import re
from bs4 import BeautifulSoup
from datetime import datetime
import sys
import concurrent.futures
from urllib.parse import urlparse

USER_AGENTS = [
    'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
    'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36',
]

def get_random_headers(referer=None):
    headers = {'User-Agent': random.choice(USER_AGENTS)}
    if referer:
        headers['Referer'] = referer
    return headers

def get_base_url():
    try:
        primary = "https://www.diziyou.one"
        resp = requests.head(primary, headers=get_random_headers(), timeout=10)
        if resp.status_code < 400:
            return primary.rstrip('/')
    except:
        pass
    
    try:
        backup = "https://www.diziyou.io"
        resp = requests.head(backup, headers=get_random_headers(), timeout=10, allow_redirects=False)
        if 300 <= resp.status_code < 400:
            location = resp.headers.get('Location', '')
            if location:
                return location.rstrip('/')
    except:
        pass
    
    return "https://www.diziyou.one".rstrip('/')

# === PARALEL SAYFA ÇEKME FONKSİYONLARI ===
def fetch_page(args):
    """Paralel sayfa çekme fonksiyonu"""
    page_num, base_url, total_pages = args
    if page_num == 1:
        url = f"{base_url}/dizi-arsivi"
    else:
        url = f"{base_url}/dizi-arsivi/page/{page_num}"
    
    try:
        headers = get_random_headers(base_url)
        resp = requests.get(url, headers=headers, timeout=15)
        resp.raise_for_status()
        return page_num, resp.content, None
    except Exception as e:
        return page_num, None, str(e)

def parse_page(content, base_url):
    """Sayfa içeriğinden dizi linklerini ayrıştır"""
    if not content:
        return []
    
    soup = BeautifulSoup(content, 'html.parser')
    series_list = []
    
    for link in soup.find_all('a', href=True, title=True):
        href = link['href'].rstrip('/')
        title = link['title'].strip()
        
        if (href.startswith(base_url) and 
            not href.endswith('/dizi-arsivi') and
            '/page/' not in href and
            title and len(title) > 2):
            
            if not any(s['url'] == href for s in series_list):
                series_list.append({
                    'name': title,
                    'url': href,
                    'poster': None
                })
    
    return series_list

# === PARALEL POSTER ÇEKME ===
def fetch_poster(series):
    """Bir dizi için poster URL'sini çek"""
    try:
        headers = get_random_headers(series['url'])
        resp = requests.get(series['url'], headers=headers, timeout=10)
        soup = BeautifulSoup(resp.content, 'html.parser')
        
        # Kapak resmini bul
        poster_div = soup.find('div', class_='category_image')
        if poster_div:
            img = poster_div.find('img', src=True)
            if img:
                return series['url'], img['src']
        
        # Alternatif arama
        for img in soup.find_all('img', class_=re.compile(r'poster|cover', re.I)):
            if 'src' in img.attrs:
                return series['url'], img['src']
                
    except Exception:
        pass
    
    return series['url'], ""

# === PARALEL BÖLÜM ÇEKME ===
def fetch_episodes(series):
    """Bir dizinin tüm bölümlerini çek"""
    series_name = series['name']
    series_url = series['url']
    poster_url = series['poster']
    
    episodes = []
    try:
        headers = get_random_headers(series_url)
        resp = requests.get(series_url, headers=headers, timeout=15)
        soup = BeautifulSoup(resp.content, 'html.parser')
        
        # Bölüm container'ını bul
        container = soup.find('div', id='scrollbar-container')
        if not container:
            return series_name, episodes
        
        for link in container.find_all('a', href=True):
            ep_url = link['href']
            if not ep_url.startswith('http'):
                continue
            
            baslik_elem = link.find('div', class_='baslik')
            tarih_elem = link.find('div', class_='tarih')
            bolumismi_elem = link.find('div', class_='bolumismi')
            
            if baslik_elem:
                raw_title = baslik_elem.text.strip()
                
                # Sezon ve bölüm numaraları
                season_num = 1
                episode_num = 1
                
                season_match = re.search(r'(\d+)\s*[.]?\s*[Ss]ezon', raw_title)
                episode_match = re.search(r'(\d+)\s*[.]?\s*[Bb]ölüm', raw_title)
                
                if season_match:
                    season_num = int(season_match.group(1))
                if episode_match:
                    episode_num = int(episode_match.group(1))
                
                episode_date = tarih_elem.text.strip() if tarih_elem else ""
                episode_name = bolumismi_elem.text.strip('() ') if bolumismi_elem else ""
                
                # TVG formatında isim
                if episode_name:
                    tvg_name = f"{series_name} S{season_num:02d}E{episode_num:02d} - {episode_name}"
                else:
                    tvg_name = f"{series_name} S{season_num:02d}E{episode_num:02d}"
                
                tvg_id = re.sub(r'[^\w]', '_', f"{series_name}_S{season_num:02d}E{episode_num:02d}")
                
                episodes.append({
                    'url': ep_url,
                    'tvg_id': tvg_id,
                    'tvg_name': tvg_name,
                    'group_title': series_name,
                    'poster': poster_url,
                    'date': episode_date
                })
        
    except Exception as e:
        print(f"    ⚠️  {series_name}: {e}")
    
    return series_name, episodes

def main():
    print("="*70)
    print("🎬 DİZİYOU M3U OLUŞTURUCU - OPTİMİZE PARALEL SÜRÜM")
    print("="*70)
    
    start_time = time.time()
    
    # 1. Ana URL
    base_url = get_base_url()
    print(f"📍 Site: {base_url}")
    
    # 2. PARALEL: Tüm sayfaları çek (87 sayfa)
    print(f"\n📥 PARALEL SAYFA ÇEKİMİ (87 sayfa)...")
    all_series = []
    
    with concurrent.futures.ThreadPoolExecutor(max_workers=10) as executor:
        # Tüm sayfa isteklerini hazırla
        page_args = [(i, base_url, 87) for i in range(1, 88)]
        
        # Paralel çalıştır ve ilerlemeyi göster
        future_to_page = {executor.submit(fetch_page, args): args for args in page_args}
        
        for i, future in enumerate(concurrent.futures.as_completed(future_to_page), 1):
            page_num, content, error = future.result()
            if error:
                print(f"   ⚠️  Sayfa {page_num}: {error}")
                continue
            
            # Sayfayı ayrıştır
            page_series = parse_page(content, base_url)
            all_series.extend(page_series)
            
            if i % 10 == 0:
                print(f"   ✅ {i}/87 sayfa işlendi, {len(all_series)} dizi bulundu")
    
    print(f"\n✅ {len(all_series)} dizi bulundu!")
    
    # 3. PARALEL: Tüm posterleri çek
    print(f"\n🖼️  PARALEL POSTER ÇEKİMİ ({len(all_series)} dizi)...")
    
    with concurrent.futures.ThreadPoolExecutor(max_workers=15) as executor:
        future_to_series = {executor.submit(fetch_poster, s): s for s in all_series}
        
        for i, future in enumerate(concurrent.futures.as_completed(future_to_series), 1):
            series_url, poster_url = future.result()
            
            # Poster URL'sini seriye kaydet
            for series in all_series:
                if series['url'] == series_url:
                    series['poster'] = poster_url
                    break
            
            if i % 50 == 0:
                print(f"   ✅ {i}/{len(all_series)} poster çekildi")
    
    # 4. PARALEL: Tüm bölümleri çek
    print(f"\n🎬 PARALEL BÖLÜM ÇEKİMİ ({len(all_series)} dizi)...")
    all_episodes = []
    
    with concurrent.futures.ThreadPoolExecutor(max_workers=20) as executor:
        future_to_episodes = {executor.submit(fetch_episodes, s): s for s in all_series}
        
        for i, future in enumerate(concurrent.futures.as_completed(future_to_episodes), 1):
            series_name, episodes = future.result()
            
            if episodes:
                all_episodes.extend(episodes)
                print(f"   ✅ {series_name[:30]:30} → {len(episodes):3} bölüm")
            
            if i % 20 == 0:
                print(f"   📊 İlerleme: {i}/{len(all_series)} dizi, {len(all_episodes)} bölüm")
    
    # 5. M3U dosyasını oluştur
    print(f"\n📁 M3U DOSYASI OLUŞTURULUYOR...")
    
    m3u_lines = [
        '#EXTM3U',
        f'#EXTCLOPT:Referer="{base_url}/"',
        '#EXTCLOPT:User-Agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"',
        f'#EXTCLOPT:Generated="{datetime.now().strftime("%Y-%m-%d %H:%M:%S")}"',
        ''
    ]
    
    for ep in all_episodes:
        extinf = f'#EXTINF:-1 tvg-id="{ep["tvg_id"]}" tvg-name="{ep["tvg_name"]}"'
        
        if ep['poster']:
            extinf += f' tvg-logo="{ep["poster"]}"'
        
        extinf += f' group-title="{ep["group_title"]}"'
        
        if ep['date']:
            extinf += f',{ep["tvg_name"]} - {ep["date"]}'
        else:
            extinf += f',{ep["tvg_name"]}'
        
        m3u_lines.append(extinf)
        m3u_lines.append(ep['url'])
    
    # 6. Dosyaya yaz
    output_file = "diziyou.m3u"
    try:
        with open(output_file, 'w', encoding='utf-8') as f:
            f.write('\n'.join(m3u_lines))
        
        total_time = time.time() - start_time
        print(f"\n{'='*70}")
        print(f"🎉 İŞLEM TAMAMLANDI!")
        print(f"⏱️  Toplam süre: {total_time/60:.1f} dakika")
        print(f"📊 {len(all_series)} dizi, {len(all_episodes)} bölüm")
        print(f"💾 {output_file} oluşturuldu")
        print(f"{'='*70}")
        
        # Örnek göster
        print("\n📋 ÖRNEK ÇIKTI (ilk 2 giriş):")
        print("-"*60)
        sample = '\n'.join(m3u_lines[:6])
        print(sample)
        print("-"*60)
        
    except Exception as e:
        print(f"\n❌ Dosya yazma hatası: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()
