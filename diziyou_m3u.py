#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
DİZİYOU M3U OLUŞTURUCU - FİNAL OPTİMİZE SÜRÜM
"""
import requests
import random
import time
import re
from bs4 import BeautifulSoup
from datetime import datetime
import sys
import concurrent.futures

# SABİT POSTER LİNKİ
SABIT_POSTER = "https://drive.google.com/uc?export=download&id=1GYNXebgh30tzFvyPYaRsUS5AVHAD8XLc"

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
    """Ana site URL'sini belirle"""
    try:
        primary = "https://www.diziyou.one"
        resp = requests.head(primary, headers=get_random_headers(), timeout=10, allow_redirects=True)
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

# === OPTİMİZE PARALEL FONKSİYONLAR ===
def fetch_dizi_page(args):
    """Bir sayfadaki tüm dizi linklerini çek"""
    page_num, base_url = args
    if page_num == 1:
        url = f"{base_url}/dizi-arsivi"
    else:
        url = f"{base_url}/dizi-arsivi/page/{page_num}"
    
    try:
        headers = get_random_headers(base_url)
        resp = requests.get(url, headers=headers, timeout=20)
        resp.raise_for_status()
        soup = BeautifulSoup(resp.content, 'html.parser')
        
        series_list = []
        for link in soup.find_all('a', href=True):
            href = link.get('href', '').rstrip('/')
            title = link.get('title', '').strip()
            
            if (href.startswith(base_url) and 
                not href.endswith('/dizi-arsivi') and
                '/page/' not in href and
                title and len(title) > 2 and
                not any(x in href for x in ['/category/', '/tag/', '/author/'])):
                
                if not any(s['url'] == href for s in series_list):
                    series_list.append({
                        'name': title,
                        'url': href
                    })
        
        return page_num, series_list, None
        
    except Exception as e:
        return page_num, [], str(e)

def fetch_episodes_for_series(series):
    """Bir dizinin tüm bölümlerini çek (POSTER ÇEKİMİ YOK)"""
    series_name = series['name']
    series_url = series['url']
    
    episodes = []
    try:
        headers = get_random_headers(series_url)
        resp = requests.get(series_url, headers=headers, timeout=25)
        soup = BeautifulSoup(resp.content, 'html.parser')
        
        # Bölümleri bul
        container = soup.find('div', id='scrollbar-container')
        if not container:
            # Alternatif container arama
            container = soup.find('div', class_=re.compile(r'episodes|bolumler|container', re.I))
        
        if container:
            for link in container.find_all('a', href=True):
                ep_url = link['href']
                if not ep_url.startswith('http'):
                    continue
                
                # Bölüm bilgilerini çıkar
                baslik = link.find('div', class_=re.compile(r'baslik|title', re.I))
                tarih = link.find('div', class_=re.compile(r'tarih|date', re.I))
                bolum_adi = link.find('div', class_=re.compile(r'bolumismi|episode-name', re.I))
                
                if baslik:
                    raw_title = baslik.text.strip()
                    
                    # Sezon ve bölüm numaraları
                    season_num = 1
                    episode_num = 1
                    
                    season_match = re.search(r'(\d+)\s*[.]?\s*[Ss]ezon', raw_title)
                    episode_match = re.search(r'(\d+)\s*[.]?\s*[Bb]ölüm', raw_title)
                    
                    if season_match:
                        season_num = int(season_match.group(1))
                    if episode_match:
                        episode_num = int(episode_match.group(1))
                    
                    episode_date = tarih.text.strip() if tarih else ""
                    episode_name = bolum_adi.text.strip('() ') if bolum_adi else ""
                    
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
                        'date': episode_date,
                        'poster': SABIT_POSTER  # SABİT POSTER KULLAN
                    })
        
    except Exception as e:
        print(f"    ⚠️  {series_name[:30]}: {str(e)[:50]}")
    
    return series_name, episodes

def main():
    print("="*70)
    print("🎬 DİZİYOU M3U OLUŞTURUCU - FİNAL OPTİMİZE SÜRÜM")
    print("="*70)
    
    start_time = time.time()
    
    # 1. Ana URL'yi al
    base_url = get_base_url()
    print(f"🌐 Site: {base_url}")
    
    # 2. TÜM SAYFALARI PARALEL ÇEK (87 sayfa)
    print(f"\n📥 87 SAYFA PARALEL ÇEKİLİYOR...")
    all_series = []
    total_pages = 87
    
    with concurrent.futures.ThreadPoolExecutor(max_workers=20) as executor:
        page_args = [(i, base_url) for i in range(1, total_pages + 1)]
        future_to_page = {executor.submit(fetch_dizi_page, args): args for args in page_args}
        
        completed = 0
        for future in concurrent.futures.as_completed(future_to_page):
            page_num, series_list, error = future.result()
            completed += 1
            
            if error:
                print(f"   ⚠️  Sayfa {page_num}: {error}")
            else:
                all_series.extend(series_list)
            
            if completed % 10 == 0:
                print(f"   ✅ {completed}/{total_pages} sayfa, {len(all_series)} dizi")
    
    # Benzersiz diziler
    unique_series = []
    seen_urls = set()
    for s in all_series:
        if s['url'] not in seen_urls:
            seen_urls.add(s['url'])
            unique_series.append(s)
    
    print(f"\n🎬 {len(unique_series)} BENZERSİZ DİZİ BULUNDU!")
    
    # 3. TÜM BÖLÜMLERİ PARALEL ÇEK (POSTER ÇEKİMİ YOK)
    print(f"\n🎥 {len(unique_series)} DİZİNİN BÖLÜMLERİ PARALEL ÇEKİLİYOR...")
    all_episodes = []
    
    with concurrent.futures.ThreadPoolExecutor(max_workers=30) as executor:
        future_to_episodes = {executor.submit(fetch_episodes_for_series, s): s for s in unique_series}
        
        completed = 0
        for future in concurrent.futures.as_completed(future_to_episodes):
            series_name, episodes = future.result()
            completed += 1
            
            if episodes:
                all_episodes.extend(episodes)
            
            if completed % 50 == 0:
                print(f"   ✅ {completed}/{len(unique_series)} dizi, {len(all_episodes)} bölüm")
    
    print(f"\n📊 TOPLAM {len(all_episodes)} BÖLÜM BULUNDU!")
    
    # 4. M3U DOSYASI OLUŞTUR
    print(f"\n💾 M3U DOSYASI OLUŞTURULUYOR...")
    
    m3u_lines = [
        '#EXTM3U x-tvg-url="https://raw.githubusercontent.com/..."',
        f'#EXTCLOPT:Referer="{base_url}/"',
        '#EXTCLOPT:User-Agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"',
        f'#EXTCLOPT:Generated="{datetime.now().strftime("%Y-%m-%d %H:%M:%S")}"',
        f'#EXTCLOPT:Poster="{SABIT_POSTER}"',
        ''
    ]
    
    for ep in all_episodes:
        # EXTINF satırı
        extinf_line = f'#EXTINF:-1 tvg-id="{ep["tvg_id"]}"'
        extinf_line += f' tvg-name="{ep["tvg_name"]}"'
        extinf_line += f' tvg-logo="{SABIT_POSTER}"'  # SABİT POSTER
        extinf_line += f' group-title="{ep["group_title"]}"'
        
        # Display title
        if ep['date']:
            extinf_line += f',{ep["tvg_name"]} ({ep["date"]})'
        else:
            extinf_line += f',{ep["tvg_name"]}'
        
        m3u_lines.append(extinf_line)
        m3u_lines.append(ep['url'])
    
    # 5. DOSYAYA KESİNLİKLE YAZ
    output_file = "diziyou.m3u"
    try:
        with open(output_file, 'w', encoding='utf-8') as f:
            f.write('\n'.join(m3u_lines))
        
        # DOSYA KONTROLÜ
        import os
        file_size = os.path.getsize(output_file)
        total_time = time.time() - start_time
        
        print(f"\n{'='*70}")
        print("🎉 İŞLEM BAŞARIYLA TAMAMLANDI!")
        print(f"{'='*70}")
        print(f"⏱️  Toplam süre: {total_time/60:.1f} dakika")
        print(f"📊 {len(unique_series)} dizi, {len(all_episodes)} bölüm")
        print(f"💾 Dosya: {output_file}")
        print(f"📏 Boyut: {file_size:,} byte ({file_size/1024/1024:.2f} MB)")
        print(f"📄 Satır: {len(m3u_lines)}")
        print(f"📍 Tam yol: {os.path.abspath(output_file)}")
        
        # KESİN DOSYA VAR MI KONTROL
        if os.path.exists(output_file):
            print(f"\n✅ DOSYA KONTROLÜ: {output_file} BAŞARIYLA OLUŞTURULDU!")
            
            # Örnek göster
            print("\n📋 İLK 3 BÖLÜM ÖRNEĞİ:")
            print("-"*60)
            with open(output_file, 'r', encoding='utf-8') as f:
                for i in range(8):
                    line = f.readline()
                    if not line:
                        break
                    print(line.rstrip())
            print("-"*60)
        else:
            print(f"\n❌ KRİTİK HATA: {output_file} DOSYASI OLUŞMADI!")
            sys.exit(1)
        
    except Exception as e:
        print(f"\n❌ DOSYA YAZMA HATASI: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

if __name__ == "__main__":
    main()
