#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
DİZİYOU M3U OLUŞTURUCU - WORKERS TAKLİTLİ SÜRÜM
"""
import requests
import random
import time
import re
from bs4 import BeautifulSoup
from datetime import datetime
import sys
import concurrent.futures

SABIT_POSTER = "https://drive.google.com/uc?export=download&id=1GYNXebgh30tzFvyPYaRsUS5AVHAD8XLc"

# WORKERS'INIZDAKİ USER-AGENT'LERİN AYNISI
USER_AGENTS = [
    'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
    'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/92.0.4512.107 Safari/537.36',
    'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.114 Safari/537.36',
    'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/14.1.2 Safari/605.1.15',
    'Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:89.0) Gecko/20100101 Firefox/89.0',
    'Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:90.0) Gecko/20100101 Firefox/90.0',
    'Mozilla/5.0 (iPhone; CPU iPhone OS 14_6 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/14.0 Mobile/15E148 Safari/604.1',
    'Mozilla/5.0 (Linux; Android 10; SM-G981B) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.88 Mobile Safari/537.36'
]

# WORKERS'INIZDAKİ GİBİ SABIT REFERER
SABIT_REFERER = "https://www.diziyou.one/"

def get_random_headers():
    """Workers'ınızdaki headers yapısının aynısı"""
    headers = {
        'User-Agent': random.choice(USER_AGENTS),
        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
        'Accept-Language': 'tr-TR,tr;q=0.9,en;q=0.8',
        'Referer': SABIT_REFERER,
        'Cache-Control': 'no-cache',
        'DNT': '1',
        'Connection': 'keep-alive',
    }
    return headers

def fetch_with_retry(url, max_retries=2):
    """Workers'ınızdaki gibi 403'te farklı User-Agent ile tekrar dene"""
    for attempt in range(max_retries + 1):
        try:
            headers = get_random_headers()
            # İlk denemede daha hızlı timeout, sonra artır
            timeout = 15 if attempt == 0 else 25
            
            resp = requests.get(url, headers=headers, timeout=timeout, allow_redirects=True)
            
            if resp.status_code == 403 and attempt < max_retries:
                print(f"      403 hatası, farklı User-Agent ile tekrar deneniyor (deneme {attempt + 2})...")
                time.sleep(random.uniform(1, 2))
                continue
                
            return resp
            
        except requests.exceptions.Timeout:
            if attempt < max_retries:
                print(f"      Timeout, tekrar deneniyor...")
                time.sleep(random.uniform(1, 2))
                continue
            raise
        except Exception as e:
            if attempt < max_retries:
                print(f"      Hata: {e}, tekrar deneniyor...")
                time.sleep(random.uniform(1, 2))
                continue
            raise
    
    return None

def get_base_url():
    """Workers'ınızdaki getBaseUrl fonksiyonunun aynısı"""
    try:
        resp = fetch_with_retry("https://www.diziyou.one")
        if resp and resp.status_code < 400:
            return "https://www.diziyou.one"
    except:
        pass
    
    try:
        resp = fetch_with_retry("https://www.diziyou.io")
        if resp and resp.status_code < 400:
            return "https://www.diziyou.io"
    except:
        pass
    
    return "https://www.diziyou.one"

def get_total_pages(base_url):
    """Sayfa sayısını bul - Workers'taki gibi regex ile"""
    try:
        url = f"{base_url}/dizi-arsivi"
        resp = fetch_with_retry(url)
        html = resp.text
        
        # Regex ile /page/X bul
        page_matches = re.findall(r'/page/(\d+)', html)
        if page_matches:
            page_numbers = [int(m) for m in page_matches]
            max_page = max(page_numbers)
            print(f"   📄 Regex ile bulunan sayfa sayısı: {max_page}")
            return max_page
        
        # Sayfa 1 / X formatı
        page_text_match = re.search(r'Sayfa\s+\d+\s*/\s*(\d+)', html, re.IGNORECASE)
        if page_text_match:
            max_page = int(page_text_match.group(1))
            print(f"   📄 Metin ile bulunan sayfa sayısı: {max_page}")
            return max_page
        
        return 107
    except Exception as e:
        print(f"   ⚠️ Sayfa sayısı bulunamadı: {e}")
        return 107

def fetch_dizi_page(page_num, base_url):
    """Sayfadaki dizileri çek - Workers regex'i ile"""
    if page_num == 1:
        url = f"{base_url}/dizi-arsivi"
    else:
        url = f"{base_url}/dizi-arsivi/page/{page_num}"
    
    try:
        resp = fetch_with_retry(url)
        html = resp.text
        
        series_list = []
        # Workers'taki gibi regex ile linkleri bul
        link_pattern = r'<a[^>]+href="([^"]+)"[^>]*title="([^"]+)"'
        
        for match in re.finditer(link_pattern, html):
            href = match.group(1)
            title = match.group(2)
            
            if (href.startswith(base_url) and 
                not href.endswith('/dizi-arsivi') and
                '/page/' not in href and
                title and len(title) > 2 and
                not any(x in href for x in ['/category/', '/tag/', '/author/'])):
                
                # Benzersiz kontrol
                if not any(s['url'] == href for s in series_list):
                    series_list.append({
                        'name': title.strip(),
                        'url': href.rstrip('/')
                    })
        
        return page_num, series_list, None
        
    except Exception as e:
        return page_num, [], str(e)

def fetch_episodes_for_series(series, base_url):
    """Bölümleri çek - Workers regex'i ile"""
    series_name = series['name']
    series_url = series['url']
    episodes = []
    
    try:
        resp = fetch_with_retry(series_url)
        html = resp.text
        
        # Scrollbar-container veya episodes class'ını bul
        container_html = html
        container_match = re.search(r'<div[^>]*id="scrollbar-container"[^>]*>([\s\S]*?)</div>', html, re.IGNORECASE)
        if container_match:
            container_html = container_match.group(1)
        else:
            container_match2 = re.search(r'<div[^>]*class="[^"]*episodes[^"]*"[^>]*>([\s\S]*?)</div>', html, re.IGNORECASE)
            if container_match2:
                container_html = container_match2.group(1)
        
        # Bölümleri regex ile bul
        episode_pattern = r'<a[^>]+href="([^"]+)"[^>]*>[\s\S]*?<div[^>]*class="[^"]*baslik[^"]*"[^>]*>([^<]+)</div>[\s\S]*?<div[^>]*class="[^"]*tarih[^"]*"[^>]*>([^<]*)</div>'
        
        for match in re.finditer(episode_pattern, container_html, re.IGNORECASE):
            ep_url = match.group(1)
            raw_title = match.group(2).strip()
            episode_date = match.group(3).strip()
            
            if not ep_url.startswith('http'):
                continue
            
            # Sezon ve bölüm numaraları
            season_num = 1
            episode_num = 1
            
            season_match = re.search(r'(\d+)\s*[.]?\s*[Ss]ezon', raw_title)
            episode_match = re.search(r'(\d+)\s*[.]?\s*[Bb]ölüm', raw_title)
            
            if season_match:
                season_num = int(season_match.group(1))
            if episode_match:
                episode_num = int(episode_match.group(1))
            
            # Bölüm adını bul
            episode_name = ""
            name_match = re.search(r'<div[^>]*class="[^"]*bolumismi[^"]*"[^>]*>([^<]+)</div>', container_html[match.start():match.start()+800], re.IGNORECASE)
            if name_match:
                episode_name = re.sub(r'[()]', '', name_match.group(1)).strip()
            
            if episode_name:
                tvg_name = f"{series_name} S{season_num:02d}-E{episode_num:02d} - {episode_name}"
            else:
                tvg_name = f"{series_name} S{season_num:02d}-E{episode_num:02d}"
            
            tvg_id = re.sub(r'[^\w]', '_', f"{series_name}_S{season_num:02d}-E{episode_num:02d}")
            
            clean_ep_url = ep_url.rstrip('/')
            final_ep_url = f"{clean_ep_url}.m3u8"
            
            episodes.append({
                'url': final_ep_url,
                'tvg_id': tvg_id,
                'tvg_name': tvg_name,
                'group_title': series_name,
                'date': episode_date,
                'poster': SABIT_POSTER
            })
        
    except Exception as e:
        print(f"    ⚠️ {series_name[:30]}: {str(e)[:50]}")
    
    return series_name, episodes

def main():
    print("="*70)
    print("🎬 DİZİYOU M3U - WORKERS TAKLİTLİ SÜRÜM")
    print("="*70)
    
    start_time = time.time()
    
    # Workers'ınızdaki gibi önce doğrudan siteyi test et
    print("\n🔍 SİTE BAĞLANTI TESTİ...")
    test_url = "https://www.diziyou.one"
    test_headers = get_random_headers()
    try:
        test_resp = requests.get(test_url, headers=test_headers, timeout=15)
        print(f"   ✅ {test_url} -> HTTP {test_resp.status_code}")
        print(f"   📱 Kullanılan User-Agent: {test_headers['User-Agent'][:50]}...")
    except Exception as e:
        print(f"   ❌ Bağlantı hatası: {e}")
    
    base_url = get_base_url()
    print(f"\n🌐 Site: {base_url}")
    
    total_pages = get_total_pages(base_url)
    print(f"📄 Toplam sayfa: {total_pages}")
    
    print(f"\n📥 {total_pages} SAYFA ÇEKİLİYOR...")
    all_series = []
    
    # Daha yavaş ve dikkatli çekim (Workers gibi)
    for page_num in range(1, total_pages + 1):
        print(f"   Sayfa {page_num}/{total_pages}...", end=" ")
        page_num, series_list, error = fetch_dizi_page(page_num, base_url)
        if error:
            print(f"❌ {error[:30]}")
        else:
            print(f"✅ {len(series_list)} dizi")
            all_series.extend(series_list)
        
        # Workers'taki gibi 500ms bekle
        time.sleep(0.5)
    
    # Benzersiz diziler
    unique_series = []
    seen_urls = set()
    for s in all_series:
        if s['url'] not in seen_urls:
            seen_urls.add(s['url'])
            unique_series.append(s)
    
    print(f"\n🎬 {len(unique_series)} BENZERSİZ DİZİ")
    
    if len(unique_series) == 0:
        print("\n❌ DİZİ BULUNAMADI!")
        sys.exit(1)
    
    # Bölümleri çek (yine yavaş ve dikkatli)
    print(f"\n🎥 BÖLÜMLER ÇEKİLİYOR...")
    all_episodes = []
    
    for i, series in enumerate(unique_series):
        print(f"   {i+1}/{len(unique_series)}: {series['name'][:40]}...", end=" ")
        series_name, episodes = fetch_episodes_for_series(series, base_url)
        if episodes:
            all_episodes.extend(episodes)
            print(f"✅ {len(episodes)} bölüm")
        else:
            print(f"⚠️ 0 bölüm")
        
        # Workers'taki gibi 300ms bekle
        time.sleep(0.3)
    
    print(f"\n📊 TOPLAM {len(all_episodes)} BÖLÜM")
    
    # M3U oluştur
    output_file = "diziyou.m3u"
    with open(output_file, 'w', encoding='utf-8') as f:
        f.write('#EXTM3U\n')
        f.write(f'#EXTCLOPT:Referer="{SABIT_REFERER}"\n')
        f.write(f'#EXTCLOPT:Generated="{datetime.now().strftime("%Y-%m-%d %H:%M:%S")}"\n\n')
        
        for ep in all_episodes:
            extinf_line = f'#EXTINF:-1 tvg-id="{ep["tvg_id"]}" tvg-name="{ep["tvg_name"]}" group-title="{ep["group_title"]}"'
            if ep['date']:
                extinf_line += f',{ep["tvg_name"]} ({ep["date"]})\n'
            else:
                extinf_line += f',{ep["tvg_name"]}\n'
            f.write(extinf_line)
            f.write(f'{ep["url"]}\n')
    
    file_size = len(open(output_file).read())
    total_time = time.time() - start_time
    
    print(f"\n{'='*70}")
    print(f"✅ TAMAMLANDI! {total_time/60:.1f} dakika")
    print(f"📊 {len(unique_series)} dizi, {len(all_episodes)} bölüm")
    print(f"💾 {output_file} ({file_size:,} byte)")
    print(f"{'='*70}")

if __name__ == "__main__":
    main()
