#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Diziyou M3U Oluşturucu
Tek script ile tüm işlemler
"""

import requests
import random
import time
import re
from bs4 import BeautifulSoup
from datetime import datetime
import sys
import os

# Rastgele User-Agent listesi
USER_AGENTS = [
    'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
    'Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:109.0) Gecko/20100101 Firefox/121.0',
    'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
    'Mozilla/5.0 (Macintosh; Intel Mac OS X 14_2) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.2 Safari/605.1.15',
    'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
]

def get_random_headers(referer=None):
    """Rastgele headers oluştur"""
    headers = {
        'User-Agent': random.choice(USER_AGENTS),
        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
        'Accept-Language': 'tr-TR,tr;q=0.9,en-US;q=0.8,en;q=0.7',
        'Accept-Encoding': 'gzip, deflate',
        'DNT': '1',
        'Connection': 'keep-alive',
        'Upgrade-Insecure-Requests': '1',
        'Cache-Control': 'max-age=0'
    }
    if referer:
        headers['Referer'] = referer
    return headers

def get_base_url():
    """Ana site URL'sini belirle"""
    primary_url = "https://www.diziyou.one/"
    backup_url = "https://www.diziyou.io/"
    
    headers = get_random_headers()
    
    # Önce ana siteyi dene
    try:
        print(f"Ana site kontrol ediliyor: {primary_url}")
        resp = requests.head(primary_url, headers=headers, timeout=10, allow_redirects=True)
        if resp.status_code < 400:
            print(f"✓ Ana site kullanılabilir: {primary_url}")
            return primary_url.rstrip('/')
    except Exception as e:
        print(f"✗ Ana siteye erişilemedi: {e}")
    
    # Yedek adresten yönlendirmeyi kontrol et
    try:
        print(f"\nYedek adres kontrol ediliyor: {backup_url}")
        resp = requests.head(backup_url, headers=headers, timeout=10, allow_redirects=False)
        
        # Yönlendirme varsa Location header'ını al
        if 300 <= resp.status_code < 400:
            location = resp.headers.get('Location', '')
            if location:
                final_url = location.rstrip('/')
                print(f"✓ Yönlendirme bulundu: {final_url}")
                return final_url
    except Exception as e:
        print(f"✗ Yedek adres kontrolü başarısız: {e}")
    
    print("ℹ Varsayılan ana site kullanılıyor")
    return primary_url.rstrip('/')

def get_all_series_links(base_url):
    """Tüm sayfalardan dizi linklerini topla"""
    series_list = []
    page = 1
    max_pages = 100  # Üst sınır
    
    print(f"\n{'='*50}")
    print("Dizi linkleri toplanıyor...")
    print(f"{'='*50}")
    
    while page <= max_pages:
        # URL oluştur
        if page == 1:
            url = f"{base_url}/dizi-arsivi"
        else:
            url = f"{base_url}/dizi-arsivi/page/{page}"
        
        headers = get_random_headers(base_url)
        
        try:
            print(f"\n📄 Sayfa {page} çekiliyor...")
            resp = requests.get(url, headers=headers, timeout=20)
            resp.raise_for_status()
            
            soup = BeautifulSoup(resp.content, 'html.parser')
            
            # Bu sayfadaki dizi linklerini bul
            page_series = []
            links = soup.find_all('a', href=True, title=True)
            
            for link in links:
                href = link.get('href', '')
                title = link.get('title', '').strip()
                
                # Sadece dizi sayfalarını filtrele
                if (href.startswith(base_url) and 
                    not href.endswith('/dizi-arsivi') and
                    not 'page/' in href and
                    title and
                    len(title) > 2):
                    
                    # Kopya kontrolü
                    if not any(s['url'] == href for s in page_series):
                        page_series.append({
                            'name': title,
                            'url': href
                        })
            
            if not page_series:
                print(f"⏹ Sayfa {page}'de dizi bulunamadı. Tarama durduruluyor.")
                break
            
            series_list.extend(page_series)
            print(f"✅ Sayfa {page}: {len(page_series)} dizi eklendi")
            
            # Sonraki sayfa için hazırlık
            page += 1
            time.sleep(1.5)  # Sunucu yükünü azalt
            
        except Exception as e:
            print(f"❌ Sayfa {page} hatası: {e}")
            break
    
    print(f"\n✅ Toplam {len(series_list)} dizi bulundu!")
    return series_list[:100]  # Test için ilk 100 dizi (tümünü almak için bu satırı kaldır)

def scrape_series_details(series_url, base_url):
    """Bir dizinin tüm sezon ve bölüm bilgilerini çek"""
    headers = get_random_headers(base_url)
    
    try:
        resp = requests.get(series_url, headers=headers, timeout=20)
        resp.raise_for_status()
        soup = BeautifulSoup(resp.content, 'html.parser')
        
        # Dizi ismini bul
        series_name = "Bilinmeyen Dizi"
        title_tag = soup.find('title')
        if title_tag:
            series_name = title_tag.text.split('|')[0].strip()
        
        # Sezon butonlarını bul
        seasons = []
        buttons_div = soup.find('div', id='butonlar')
        if buttons_div:
            season_buttons = buttons_div.find_all('button', class_='btn')
            for btn in season_buttons:
                season_text = btn.get('search-text', '').strip() or btn.text.strip()
                if season_text:
                    seasons.append(season_text)
        
        # Eğer sezon bulunamadıysa varsayılan ekle
        if not seasons:
            seasons = ['1. Sezon']
        
        # Bölümleri çek
        episodes = []
        episodes_container = soup.find('div', id='scrollbar-container')
        
        if episodes_container:
            episode_links = episodes_container.find_all('a', href=True)
            
            for ep_link in episode_links:
                ep_url = ep_link.get('href', '')
                if not ep_url.startswith('http'):
                    continue
                
                # Bölüm bilgilerini çıkar
                baslik_div = ep_link.find('div', class_='baslik')
                tarih_div = ep_link.find('div', class_='tarih')
                bolumismi_div = ep_link.find('div', class_='bolumismi')
                
                if baslik_div:
                    episode_title = baslik_div.text.strip()
                    
                    # Sezon ve bölüm numaralarını çıkar
                    season_num = 1
                    episode_num = 1
                    
                    # Regex ile sezon ve bölüm numaralarını bul
                    season_match = re.search(r'(\d+)\s*[.]?\s*[Ss]ezon', episode_title)
                    episode_match = re.search(r'(\d+)\s*[.]?\s*[Bb]ölüm', episode_title)
                    
                    if season_match:
                        season_num = int(season_match.group(1))
                    if episode_match:
                        episode_num = int(episode_match.group(1))
                    
                    episode_date = tarih_div.text.strip() if tarih_div else "Tarih Yok"
                    episode_name = bolumismi_div.text.strip('() ') if bolumismi_div else ""
                    
                    # Formatlı bölüm ismi oluştur
                    formatted_title = f"{series_name} - {season_num}. Sezon {episode_num}. Bölüm"
                    if episode_name:
                        formatted_title += f" - ({episode_name})"
                    if episode_date != "Tarih Yok":
                        formatted_title += f" - {episode_date}"
                    
                    episodes.append({
                        'series_name': series_name,
                        'url': ep_url,
                        'title': formatted_title,
                        'season': season_num,
                        'episode': episode_num,
                        'date': episode_date,
                        'raw_title': episode_title
                    })
        
        return {
            'name': series_name,
            'url': series_url,
            'seasons': seasons,
            'episodes': episodes
        }
        
    except Exception as e:
        print(f"  ❌ Hata: {e}")
        return {
            'name': "Hatalı Dizi",
            'url': series_url,
            'seasons': [],
            'episodes': []
        }

def generate_m3u(all_series_data, base_url):
    """M3U dosyası içeriğini oluştur"""
    print(f"\n{'='*50}")
    print("M3U dosyası oluşturuluyor...")
    print(f"{'='*50}")
    
    m3u_lines = [
        '#EXTM3U',
        f'#EXTCLOPT:Referer="{base_url}/"',
        '#EXTCLOPT:User-Agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"',
        f'#EXTCLOPT:Generated="{datetime.now().strftime("%Y-%m-%d %H:%M:%S")}"',
        ''
    ]
    
    total_episodes = 0
    
    for series in all_series_data:
        if not series['episodes']:
            continue
            
        series_name = series['name']
        print(f"📺 {series_name}: {len(series['episodes'])} bölüm")
        
        # Grup başlığı (isteğe bağlı, bazı oynatıcılar destekler)
        m3u_lines.append(f'#EXTGRP:{series_name}')
        
        for episode in series['episodes']:
            m3u_lines.append(f'#EXTINF:-1, {episode["title"]}')
            m3u_lines.append(episode['url'])
            total_episodes += 1
    
    print(f"\n✅ Toplam {total_episodes} bölüm M3U'ya eklendi!")
    
    return '\n'.join(m3u_lines)

def main():
    """Ana fonksiyon"""
    print("="*60)
    print("DİZİYOU M3U OLUŞTURUCU")
    print("="*60)
    
    # 1. Ana URL'yi belirle
    base_url = get_base_url()
    
    # 2. Tüm dizi linklerini al
    series_links = get_all_series_links(base_url)
    
    if not series_links:
        print("\n❌ Hiç dizi bulunamadı! Script durduruluyor.")
        return
    
    # 3. Her dizi için detayları çek
    print(f"\n{'='*50}")
    print("Dizi detayları çekiliyor...")
    print(f"{'='*50}")
    
    all_series_data = []
    for i, series in enumerate(series_links[:50], 1):  # İlk 50 dizi (tümü için [:50] kaldır)
        print(f"\n[{i}/{min(50, len(series_links))}] {series['name']}")
        series_data = scrape_series_details(series['url'], base_url)
        all_series_data.append(series_data)
        time.sleep(1)  # Sunucu yükünü azalt
    
    # 4. M3U oluştur
    m3u_content = generate_m3u(all_series_data, base_url)
    
    # 5. Dosyaya yaz
    output_file = "diziyou.m3u"
    try:
        with open(output_file, 'w', encoding='utf-8') as f:
            f.write(m3u_content)
        print(f"\n✅ M3U dosyası başarıyla oluşturuldu: {output_file}")
        print(f"📁 Dosya boyutu: {len(m3u_content)} karakter")
        
        # Dosyadan örnek göster
        print(f"\n📄 M3U Önizleme (ilk 5 satır):")
        print("-"*40)
        lines = m3u_content.split('\n')[:7]
        for line in lines:
            print(line)
        print("-"*40)
        
    except Exception as e:
        print(f"\n❌ Dosya yazma hatası: {e}")

if __name__ == "__main__":
    main()
