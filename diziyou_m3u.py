#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
DİZİYOU M3U OLUŞTURUCU - GITHUB ACTIONS UYUMLU (DİNAMİK SAYFA SAYISI)
"""
import requests
import random
import time
import re
from bs4 import BeautifulSoup
from datetime import datetime
import sys
import concurrent.futures
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

# SABİT POSTER LİNKİ
SABIT_POSTER = "https://drive.google.com/uc?export=download&id=1GYNXebgh30tzFvyPYaRsUS5AVHAD8XLc"

# GENİŞLETİLMİŞ USER-AGENT LİSTESİ
USER_AGENTS = [
    'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
    'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
    'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
    'Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:121.0) Gecko/20100101 Firefox/121.0',
    'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.1 Safari/605.1.15',
    'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.0.0 Safari/537.36 Edg/119.0.0.0',
]

def get_retry_session(retries=3, backoff_factor=0.5):
    """Retry mekanizmalı session oluştur"""
    session = requests.Session()
    retry = Retry(
        total=retries,
        read=retries,
        connect=retries,
        backoff_factor=backoff_factor,
        status_forcelist=[429, 500, 502, 503, 504, 403],
        allowed_methods=["HEAD", "GET", "OPTIONS"]
    )
    adapter = HTTPAdapter(max_retries=retry)
    session.mount('http://', adapter)
    session.mount('https://', adapter)
    return session

def get_random_headers(referer=None):
    """Rastgele headers oluştur - Geliştirilmiş versiyon"""
    headers = {
        'User-Agent': random.choice(USER_AGENTS),
        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
        'Accept-Language': 'tr-TR,tr;q=0.9,en;q=0.8',
        'Accept-Encoding': 'gzip, deflate, br',
        'DNT': '1',
        'Connection': 'keep-alive',
        'Upgrade-Insecure-Requests': '1',
        'Cache-Control': 'max-age=0',
    }
    if referer:
        headers['Referer'] = referer
    else:
        headers['Referer'] = 'https://www.google.com/'
    return headers

def get_base_url():
    """Ana site URL'sini belirle - Geliştirilmiş"""
    session = get_retry_session()
    
    # Önce .one domainini dene
    try:
        primary = "https://www.diziyou.one"
        headers = get_random_headers()
        resp = session.head(primary, headers=headers, timeout=15, allow_redirects=True)
        if resp.status_code < 400:
            return primary.rstrip('/')
    except:
        pass
    
    # .io domainini dene
    try:
        backup = "https://www.diziyou.io"
        headers = get_random_headers()
        resp = session.head(backup, headers=headers, timeout=15, allow_redirects=False)
        if 300 <= resp.status_code < 400:
            location = resp.headers.get('Location', '')
            if location:
                return location.rstrip('/')
    except:
        pass
    
    return "https://www.diziyou.one".rstrip('/')

def get_total_pages(base_url):
    """Toplam sayfa sayısını dinamik olarak bul"""
    try:
        session = get_retry_session()
        headers = get_random_headers(base_url)
        
        # İlk sayfayı çek
        url = f"{base_url}/dizi-arsivi"
        resp = session.get(url, headers=headers, timeout=30)
        
        if resp.status_code == 403:
            time.sleep(2)
            headers = get_random_headers(base_url)
            headers['User-Agent'] = 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
            resp = session.get(url, headers=headers, timeout=30)
        
        soup = BeautifulSoup(resp.content, 'html.parser')
        
        # Sayfalama bilgisini bul
        # Yöntem 1: Sayfalama div'i içindeki son sayfa numarası
        pagination = soup.find('div', class_=re.compile(r'pagination|sayfalama|nav-links', re.I))
        if pagination:
            # Son sayfa linkini bul
            page_links = pagination.find_all('a', href=True)
            page_numbers = []
            for link in page_links:
                # page/X veya /page/X formatını ara
                page_match = re.search(r'/page/(\d+)', link['href'])
                if page_match:
                    page_numbers.append(int(page_match.group(1)))
            
            if page_numbers:
                return max(page_numbers)
        
        # Yöntem 2: "Sayfa 1 / X" formatını ara
        page_text = soup.find(text=re.compile(r'Sayfa\s+\d+\s*/\s*(\d+)', re.I))
        if page_text:
            match = re.search(r'Sayfa\s+\d+\s*/\s*(\d+)', page_text, re.I)
            if match:
                return int(match.group(1))
        
        # Yöntem 3: Son sayfa butonunu bul
        last_page_link = soup.find('a', text=re.compile(r'Son|Last|»»', re.I))
        if last_page_link and last_page_link.get('href'):
            match = re.search(r'/page/(\d+)', last_page_link['href'])
            if match:
                return int(match.group(1))
        
        # Yöntem 4: Varsayılan olarak 100 sayfa dene, bulamazsak 150
        # Önce 100'e kadar sayfaları kontrol et
        print("   🔍 Sayfa sayısı tespit edilemedi, taranıyor...")
        for test_page in [50, 100, 150, 200]:
            test_url = f"{base_url}/dizi-arsivi/page/{test_page}"
            resp_test = session.get(test_url, headers=headers, timeout=30)
            if resp_test.status_code == 404:
                return test_page - 1
            time.sleep(0.5)
        
        return 150  # Varsayılan
        
    except Exception as e:
        print(f"   ⚠️ Sayfa sayısı tespit hatası: {e}, varsayılan 107 kullanılıyor")
        return 107  # Son bilinen sayfa sayısı

def fetch_dizi_page(args):
    """Bir sayfadaki tüm dizi linklerini çek - Geliştirilmiş"""
    page_num, base_url = args
    
    if page_num == 1:
        url = f"{base_url}/dizi-arsivi"
    else:
        url = f"{base_url}/dizi-arsivi/page/{page_num}"
    
    session = get_retry_session()
    
    try:
        # Rastgele bekleme (GitHub Actions için)
        time.sleep(random.uniform(0.3, 0.8))
        
        headers = get_random_headers(base_url)
        resp = session.get(url, headers=headers, timeout=30)
        
        # 403 hatası alınırsa, farklı User-Agent ile dene
        if resp.status_code == 403:
            time.sleep(random.uniform(1, 2))
            headers = get_random_headers(base_url)
            headers['User-Agent'] = 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
            resp = session.get(url, headers=headers, timeout=30)
        
        resp.raise_for_status()
        soup = BeautifulSoup(resp.content, 'html.parser')
        
        series_list = []
        for link in soup.find_all('a', href=True):
            href = link.get('href', '').rstrip('/')
            title = link.get('title', '').strip()
            
            # Alternatif: text'ten de almayı dene
            if not title and link.text:
                title = link.text.strip()
            
            if (href.startswith(base_url) and 
                not href.endswith('/dizi-arsivi') and
                '/page/' not in href and
                title and len(title) > 2 and
                not any(x in href for x in ['/category/', '/tag/', '/author/', '/bolum', '/episode'])):
                
                if not any(s['url'] == href for s in series_list):
                    series_list.append({
                        'name': title,
                        'url': href
                    })
        
        return page_num, series_list, None
        
    except Exception as e:
        return page_num, [], str(e)

def fetch_episodes_for_series(series):
    """Bir dizinin tüm bölümlerini çek - TÜM DÜZELTMELER BURADA"""
    series_name = series['name']
    series_url = series['url']
    
    episodes = []
    session = get_retry_session()
    
    try:
        # Rastgele bekleme
        time.sleep(random.uniform(0.2, 0.5))
        
        headers = get_random_headers(series_url)
        resp = session.get(series_url, headers=headers, timeout=30)
        
        if resp.status_code == 403:
            time.sleep(random.uniform(1, 2))
            headers = get_random_headers(series_url)
            headers['User-Agent'] = 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
            resp = session.get(series_url, headers=headers, timeout=30)
        
        soup = BeautifulSoup(resp.content, 'html.parser')
        
        # Bölümleri bul
        container = soup.find('div', id='scrollbar-container')
        if not container:
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
                    
                    # HER BÖLÜMÜN KENDİ TARİHİ - DÜZELTME 1
                    episode_date = tarih.text.strip() if tarih else ""
                    
                    # Tarihi temizle (gereksiz boşlukları kaldır)
                    if episode_date:
                        episode_date = ' '.join(episode_date.split())
                    
                    episode_name = bolum_adi.text.strip('() ') if bolum_adi else ""
                    
                    # TVG formatında isim - S01-E01 formatında
                    if episode_name:
                        tvg_name = f"{series_name} S{season_num:02d}-E{episode_num:02d} - {episode_name}"
                    else:
                        tvg_name = f"{series_name} S{season_num:02d}-E{episode_num:02d}"
                    
                    # TVG ID - S01-E01 formatında
                    tvg_id = re.sub(r'[^\w]', '_', f"{series_name}_S{season_num:02d}-E{episode_num:02d}")
                    
                    # URL DÜZELTMELERİ - DÜZELTME 2 ve 3
                    # 1. Sonundaki / karakterini temizle
                    clean_ep_url = ep_url.rstrip('/')
                    # 2. Sonuna .m3u8 ekle
                    final_ep_url = f"{clean_ep_url}.m3u8"
                    
                    episodes.append({
                        'url': final_ep_url,  # DÜZELTİLMİŞ URL
                        'tvg_id': tvg_id,
                        'tvg_name': tvg_name,
                        'group_title': series_name,
                        'date': episode_date,  # HER BÖLÜMÜN KENDİ TARİHİ
                        'poster': SABIT_POSTER
                    })
        
    except Exception as e:
        print(f"    ⚠️  {series_name[:30]}: {str(e)[:50]}")
    
    return series_name, episodes

def main():
    print("="*70)
    print("🎬 DİZİYOU M3U OLUŞTURUCU - GITHUB ACTIONS UYUMLU (DİNAMİK)")
    print("="*70)
    
    start_time = time.time()
    
    # 1. Ana URL'yi al
    base_url = get_base_url()
    print(f"🌐 Site: {base_url}")
    
    # 2. TOPLAM SAYFA SAYISINI DİNAMİK BUL
    print(f"\n🔍 TOPLAM SAYFA SAYISI TESPİT EDİLİYOR...")
    total_pages = get_total_pages(base_url)
    print(f"📄 TOPLAM {total_pages} SAYFA BULUNDU!")
    
    # 3. TÜM SAYFALARI PARALEL ÇEK
    print(f"\n📥 {total_pages} SAYFA PARALEL ÇEKİLİYOR...")
    all_series = []
    
    # Daha az thread kullan (GitHub Actions için optimize)
    with concurrent.futures.ThreadPoolExecutor(max_workers=10) as executor:
        page_args = [(i, base_url) for i in range(1, total_pages + 1)]
        future_to_page = {executor.submit(fetch_dizi_page, args): args for args in page_args}
        
        completed = 0
        failed_pages = []
        
        for future in concurrent.futures.as_completed(future_to_page):
            page_num, series_list, error = future.result()
            completed += 1
            
            if error:
                print(f"   ⚠️  Sayfa {page_num}: {error}")
                failed_pages.append(page_num)
                # Hata alınan sayfalar için tekrar deneme yap
                if "403" in error:
                    print(f"   🔄 Sayfa {page_num} tekrar deneniyor...")
                    time.sleep(2)
                    page_num2, series_list2, error2 = fetch_dizi_page((page_num, base_url))
                    if not error2:
                        all_series.extend(series_list2)
                        print(f"   ✅ Sayfa {page_num} başarıyla alındı (2. deneme)")
                        failed_pages.remove(page_num)
            else:
                all_series.extend(series_list)
            
            if completed % 20 == 0 or completed == total_pages:
                print(f"   ✅ {completed}/{total_pages} sayfa, {len(all_series)} dizi")
        
        if failed_pages:
            print(f"   ⚠️ {len(failed_pages)} sayfa alınamadı: {failed_pages[:10]}")
    
    # Benzersiz diziler
    unique_series = []
    seen_urls = set()
    for s in all_series:
        if s['url'] not in seen_urls:
            seen_urls.add(s['url'])
            unique_series.append(s)
    
    print(f"\n🎬 {len(unique_series)} BENZERSİZ DİZİ BULUNDU!")
    
    if len(unique_series) == 0:
        print("\n❌ HİÇ DİZİ BULUNAMADI! Site yapısı değişmiş olabilir.")
        sys.exit(1)
    
    # 4. TÜM BÖLÜMLERİ PARALEL ÇEK
    print(f"\n🎥 {len(unique_series)} DİZİNİN BÖLÜMLERİ PARALEL ÇEKİLİYOR...")
    all_episodes = []
    
    # Daha az thread kullan (GitHub Actions için)
    with concurrent.futures.ThreadPoolExecutor(max_workers=15) as executor:
        future_to_episodes = {executor.submit(fetch_episodes_for_series, s): s for s in unique_series}
        
        completed = 0
        for future in concurrent.futures.as_completed(future_to_episodes):
            series_name, episodes = future.result()
            completed += 1
            
            if episodes:
                all_episodes.extend(episodes)
            
            if completed % 50 == 0 or completed == len(unique_series):
                print(f"   ✅ {completed}/{len(unique_series)} dizi, {len(all_episodes)} bölüm")
    
    print(f"\n📊 TOPLAM {len(all_episodes)} BÖLÜM BULUNDU!")
    
    if len(all_episodes) == 0:
        print("\n❌ HİÇ BÖLÜM BULUNAMADI!")
        sys.exit(1)
    
    # 5. M3U DOSYASI OLUŞTUR
    print(f"\n💾 M3U DOSYASI OLUŞTURULUYOR...")
    
    m3u_lines = [
        '#EXTM3U',
        f'#EXTCLOPT:Referer="{base_url}/"',
        '#EXTCLOPT:User-Agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"',
        f'#EXTCLOPT:Generated="{datetime.now().strftime("%Y-%m-%d %H:%M:%S")}"',
        f'#EXTCLOPT:TotalSeries={len(unique_series)}',
        f'#EXTCLOPT:TotalEpisodes={len(all_episodes)}',
        f'#EXTCLOPT:TotalPages={total_pages}',
        ''
    ]
    
    for ep in all_episodes:
        # EXTINF satırı - S01-E01 formatında
        extinf_line = f'#EXTINF:-1 tvg-id="{ep["tvg_id"]}"'
        extinf_line += f' tvg-name="{ep["tvg_name"]}"'
        extinf_line += f' group-title="{ep["group_title"]}"'
        
        # Display title - HER BÖLÜMÜN KENDİ TARİHİ İLE
        if ep['date']:
            extinf_line += f',{ep["tvg_name"]} ({ep["date"]})'
        else:
            extinf_line += f',{ep["tvg_name"]}'
        
        m3u_lines.append(extinf_line)
        m3u_lines.append(ep['url'])  # DÜZELTİLMİŞ URL (.m3u8'li)
    
    # 6. DOSYAYA KESİNLİKLE YAZ
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
        print(f"📄 Toplam sayfa: {total_pages}")
        print(f"🎬 Toplam dizi: {len(unique_series)}")
        print(f"📺 Toplam bölüm: {len(all_episodes)}")
        print(f"💾 Dosya: {output_file}")
        print(f"📏 Boyut: {file_size:,} byte ({file_size/1024/1024:.2f} MB)")
        print(f"📄 Satır: {len(m3u_lines)}")
        
        if os.path.exists(output_file) and file_size > 1000:
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
            print(f"\n❌ DOSYA OLUŞTU AMA BOYUT ÇOK KÜÇÜK!")
            sys.exit(1)
        
    except Exception as e:
        print(f"\n❌ DOSYA YAZMA HATASI: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

if __name__ == "__main__":
    main()
