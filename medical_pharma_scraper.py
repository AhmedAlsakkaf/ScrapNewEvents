"""
🎯 MEDICAL & PHARMA EVENT ORGANIZERS SCRAPER
============================================
Clean, production-ready scraper for business development leads
- Focuses on VERIFIED organizer information
- Easy to configure scraping numbers
- Built-in data validation
- Real-time verification checks

Author: Business Development Scraper
Date: September 2025
"""

import requests
from bs4 import BeautifulSoup
import csv
import pandas as pd
import re
from urllib.parse import urljoin
import time
from datetime import datetime
import json

# ==========================================
# 🎛️ CONFIGURATION PANEL - CHANGE HERE!
# ==========================================

# 🔢 MAIN CONTROL: Number of events to scrape
EVENTS_TO_SCRAPE = 10  # 👈 CHANGE THIS NUMBER (5, 10, 20, 50, 100)

# 🌍 VPN/LOCATION SETTINGS
USE_STEALTH_MODE = True  # Enhanced headers to avoid blocking
REQUEST_DELAY = 2  # Seconds between requests (increase if getting blocked)

# 📁 OUTPUT FILES
OUTPUT_CSV = "verified_event_organizers.csv"
VALIDATION_LOG = "data_validation_log.txt"

# ==========================================
# 🔧 SCRAPING FUNCTIONS
# ==========================================

def get_stealth_headers():
    """Enhanced headers to avoid geo-blocking and bot detection"""
    return {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8',
        'Accept-Language': 'en-US,en;q=0.9',
        'Accept-Encoding': 'gzip, deflate, br',
        'DNT': '1',
        'Connection': 'keep-alive',
        'Upgrade-Insecure-Requests': '1',
        'Sec-Fetch-Dest': 'document',
        'Sec-Fetch-Mode': 'navigate',
        'Sec-Fetch-Site': 'none',
        'Sec-Fetch-User': '?1',
        'Cache-Control': 'max-age=0',
        'Referer': 'https://google.com'
    }

def validate_url(url):
    """Check if a URL is reachable and valid"""
    try:
        response = requests.head(url, headers=get_stealth_headers(), timeout=10)
        return response.status_code in [200, 301, 302]
    except:
        return False

def validate_email_format(email):
    """Basic email format validation"""
    pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
    return re.match(pattern, email) is not None

def extract_organizer_details(event_url, headers):
    """
    Extract organizer information from individual event pages
    """
    organizer_info = {
        'organiser_name': 'N/A',
        'organiser_website': 'N/A', 
        'organiser_email': 'N/A',
        'contact_person': 'N/A',
        'verification_status': 'Unverified'
    }
    
    try:
        print(f"    🔍 Extracting organizer details from: {event_url[:60]}...")
        
        response = requests.get(event_url, headers=headers, timeout=15)
        response.raise_for_status()
        
        soup = BeautifulSoup(response.content, 'html.parser')
        
        # Method 1: Look for organizer sections
        organizer_keywords = ['organizer', 'organised by', 'organiser', 'hosted by', 'presented by']
        for keyword in organizer_keywords:
            sections = soup.find_all(text=re.compile(keyword, re.IGNORECASE))
            for section in sections[:2]:  # Check first 2 matches
                parent = section.parent
                if parent:
                    # Look for links near organizer mentions
                    next_elements = parent.find_next_siblings()[:3]
                    for element in next_elements:
                        link = element.find('a')
                        if link and link.get('href'):
                            href = link.get('href')
                            if not href.startswith('mailto:') and 'http' in href:
                                organizer_info['organiser_website'] = href
                                organizer_info['organiser_name'] = link.get_text(strip=True) or href.split('//')[1].split('/')[0]
                                organizer_info['verification_status'] = 'Website_Found'
                                break
        
        # Method 2: Look for email addresses
        email_pattern = r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b'
        emails = re.findall(email_pattern, str(soup))
        
        if emails:
            # Filter out common non-organizer emails
            filtered_emails = [e for e in emails if not any(x in e.lower() for x in ['facebook', 'twitter', 'linkedin', 'google', 'youtube'])]
            if filtered_emails:
                organizer_info['organiser_email'] = filtered_emails[0]
                organizer_info['verification_status'] = 'Email_Found'
        
        # Method 3: Look for contact pages or about pages
        contact_links = soup.find_all('a', text=re.compile(r'contact|about|organizer', re.IGNORECASE))
        for link in contact_links[:2]:
            href = link.get('href')
            if href and not href.startswith('mailto:'):
                full_url = urljoin(event_url, href)
                if validate_url(full_url):
                    organizer_info['organiser_website'] = full_url
                    organizer_info['verification_status'] = 'Contact_Page_Found'
                    break
        
        time.sleep(REQUEST_DELAY)
        
    except Exception as e:
        print(f"      ❌ Error extracting organizer details: {str(e)}")
        organizer_info['verification_status'] = f'Error: {str(e)[:50]}'
    
    return organizer_info

def extract_event_data_from_card(card, headers):
    """Extract event data from 10times.com event card"""
    event_data = {}
    
    try:
        # Extract event date
        date_td = card.find('td', class_='text-dark')
        if date_td:
            event_data['event_date'] = date_td.get_text(strip=True)
        else:
            event_data['event_date'] = 'N/A'
        
        # Extract event link and name
        clickable_td = card.find('td', {'onclick': True})
        if clickable_td:
            onclick_content = clickable_td.get('onclick', '')
            url_match = re.search(r"window\.open\(['\"]([^'\"]+)['\"]", onclick_content)
            if url_match:
                event_data['event_link'] = url_match.group(1)
                # Extract event name from URL
                event_name = event_data['event_link'].split('/')[-1]
                event_name = re.sub(r'-+', ' ', event_name).title().strip()
                event_data['event_name'] = event_name
            else:
                event_data['event_link'] = 'N/A'
                event_data['event_name'] = 'N/A'
        else:
            event_data['event_link'] = 'N/A'
            event_data['event_name'] = 'N/A'
        
        # Extract location
        venue_link = card.find('div', class_='venue')
        if venue_link:
            venue_a = venue_link.find('a')
            if venue_a:
                location = venue_a.get_text(strip=True)
                # Try to parse city and state
                if ',' in location:
                    parts = location.split(',')
                    event_data['city'] = parts[0].strip()
                    event_data['state'] = parts[-1].strip() if len(parts) > 1 else 'N/A'
                else:
                    event_data['city'] = location
                    event_data['state'] = 'N/A'
            else:
                event_data['city'] = venue_link.get_text(strip=True)
                event_data['state'] = 'N/A'
        else:
            event_data['city'] = 'N/A'
            event_data['state'] = 'N/A'
        
        return event_data
        
    except Exception as e:
        print(f"      ❌ Error extracting event data: {str(e)}")
        return None

def scrape_10times_medical_pharma():
    """Main scraping function for 10times.com medical pharma events"""
    
    url = "https://10times.com/usa/medical-pharma"
    headers = get_stealth_headers()
    
    print(f"🎯 MEDICAL & PHARMA ORGANIZER SCRAPER")
    print(f"📍 Target: {url}")
    print(f"📊 Events to scrape: {EVENTS_TO_SCRAPE}")
    print(f"⏰ Request delay: {REQUEST_DELAY} seconds")
    print("=" * 70)
    
    try:
        print("🌐 Fetching main event listing page...")
        response = requests.get(url, headers=headers, timeout=30)
        response.raise_for_status()
        print(f"✅ Page fetched successfully (Status: {response.status_code})")
        
        soup = BeautifulSoup(response.content, 'html.parser')
        event_cards = soup.find_all('tr', class_=lambda x: x and 'event-card' in x)
        
        print(f"🔍 Found {len(event_cards)} event cards")
        event_cards = event_cards[:EVENTS_TO_SCRAPE]
        
        scraped_data = []
        validation_log = []
        
        for i, card in enumerate(event_cards, 1):
            try:
                print(f"\n📋 Processing Event {i}/{len(event_cards)}")
                
                # Extract basic event info
                event_data = extract_event_data_from_card(card, headers)
                
                if not event_data or event_data['event_name'] == 'N/A':
                    print(f"    ❌ Could not extract basic event data")
                    continue
                
                print(f"    📅 Event: {event_data['event_name']}")
                print(f"    📍 Location: {event_data['city']}, {event_data['state']}")
                print(f"    🔗 Link: {event_data['event_link']}")
                
                # Get organizer details
                organizer_info = {'organiser_name': 'N/A', 'organiser_website': 'N/A', 'organiser_email': 'N/A', 'verification_status': 'No_Details'}
                
                if event_data['event_link'] != 'N/A':
                    organizer_info = extract_organizer_details(event_data['event_link'], headers)
                
                # Combine data
                combined_data = {**event_data, **organizer_info}
                
                # Validation
                validation_notes = []
                if organizer_info['organiser_website'] != 'N/A':
                    if validate_url(organizer_info['organiser_website']):
                        validation_notes.append("Website_Valid")
                    else:
                        validation_notes.append("Website_Invalid")
                
                if organizer_info['organiser_email'] != 'N/A':
                    if validate_email_format(organizer_info['organiser_email']):
                        validation_notes.append("Email_Format_Valid")
                    else:
                        validation_notes.append("Email_Format_Invalid")
                
                combined_data['validation_notes'] = ', '.join(validation_notes)
                
                scraped_data.append(combined_data)
                
                # Log for validation
                log_entry = f"Event {i}: {event_data['event_name']} | Status: {organizer_info['verification_status']} | Notes: {combined_data['validation_notes']}"
                validation_log.append(log_entry)
                
                print(f"    ✅ Status: {organizer_info['verification_status']}")
                
            except Exception as e:
                print(f"    ❌ Error processing event {i}: {str(e)}")
                continue
        
        # Save validation log
        with open(VALIDATION_LOG, 'w', encoding='utf-8') as log_file:
            log_file.write("EVENT ORGANIZER SCRAPING VALIDATION LOG\n")
            log_file.write(f"Scraped on: {datetime.now()}\n")
            log_file.write(f"Total events processed: {len(scraped_data)}\n\n")
            for entry in validation_log:
                log_file.write(entry + "\n")
        
        print(f"\n🎉 Scraping completed!")
        print(f"📊 Successfully processed: {len(scraped_data)} events")
        print(f"📋 Validation log saved: {VALIDATION_LOG}")
        
        return scraped_data
        
    except requests.RequestException as e:
        print(f"❌ Network error: {str(e)}")
        if "403" in str(e):
            print("🌍 This might be due to geo-blocking. Try using a VPN!")
        return []
    except Exception as e:
        print(f"❌ Unexpected error: {str(e)}")
        return []

def save_to_csv_with_validation(data):
    """Save scraped data to CSV with validation summary"""
    
    if not data:
        print("❌ No data to save!")
        return None
    
    # Prepare CSV data
    csv_headers = [
        'Event Name', 'Date', 'City', 'State', 
        'Organiser Name', 'Organiser Website', 'Organiser Email', 
        'Event Link', 'Verification Status', 'Validation Notes'
    ]
    
    csv_data = []
    for event in data:
        csv_row = {
            'Event Name': event.get('event_name', 'N/A'),
            'Date': event.get('event_date', 'N/A'),
            'City': event.get('city', 'N/A'),
            'State': event.get('state', 'N/A'),
            'Organiser Name': event.get('organiser_name', 'N/A'),
            'Organiser Website': event.get('organiser_website', 'N/A'),
            'Organiser Email': event.get('organiser_email', 'N/A'),
            'Event Link': event.get('event_link', 'N/A'),
            'Verification Status': event.get('verification_status', 'N/A'),
            'Validation Notes': event.get('validation_notes', 'N/A')
        }
        csv_data.append(csv_row)
    
    # Save to CSV
    with open(OUTPUT_CSV, 'w', newline='', encoding='utf-8') as csvfile:
        writer = csv.DictWriter(csvfile, fieldnames=csv_headers)
        writer.writeheader()
        writer.writerows(csv_data)
    
    # Create DataFrame for analysis
    df = pd.DataFrame(csv_data)
    
    # Validation summary
    print(f"\n📊 DATA QUALITY SUMMARY:")
    print("=" * 50)
    print(f"✅ Total events: {len(df)}")
    print(f"🏢 Events with organizer names: {(df['Organiser Name'] != 'N/A').sum()}")
    print(f"🌐 Events with websites: {(df['Organiser Website'] != 'N/A').sum()}")
    print(f"✉️  Events with emails: {(df['Organiser Email'] != 'N/A').sum()}")
    print(f"📍 Events with location: {(df['City'] != 'N/A').sum()}")
    
    # Verification status breakdown
    print(f"\n🔍 VERIFICATION STATUS BREAKDOWN:")
    status_counts = df['Verification Status'].value_counts()
    for status, count in status_counts.items():
        print(f"    {status}: {count}")
    
    # Show sample data
    print(f"\n📋 SAMPLE DATA PREVIEW:")
    print("-" * 80)
    pd.set_option('display.max_columns', None)
    pd.set_option('display.width', None)
    pd.set_option('display.max_colwidth', 40)
    print(df[['Event Name', 'City', 'Organiser Name', 'Verification Status']].head())
    
    print(f"\n✅ Data saved to: {OUTPUT_CSV}")
    return df

# ==========================================
# 🚀 MAIN EXECUTION
# ==========================================

if __name__ == "__main__":
    print("🎯 MEDICAL & PHARMA EVENT ORGANIZER SCRAPER")
    print("=" * 60)
    print(f"📊 Configuration:")
    print(f"   Events to scrape: {EVENTS_TO_SCRAPE}")
    print(f"   Output file: {OUTPUT_CSV}")
    print(f"   Request delay: {REQUEST_DELAY} seconds")
    print(f"   Stealth mode: {USE_STEALTH_MODE}")
    print("=" * 60)
    
    # Start scraping
    organizer_data = scrape_10times_medical_pharma()
    
    if organizer_data:
        # Save and validate data
        df_results = save_to_csv_with_validation(organizer_data)
        
        print(f"\n🎉 SCRAPING COMPLETED SUCCESSFULLY!")
        print(f"📁 Files created:")
        print(f"   • {OUTPUT_CSV} (Main data)")
        print(f"   • {VALIDATION_LOG} (Validation log)")
        print(f"\n💡 Next steps:")
        print(f"   1. Review the validation log for data quality")
        print(f"   2. Cross-check event dates with official sources")
        print(f"   3. Verify organizer contact information")
        print(f"   4. Scale up by changing EVENTS_TO_SCRAPE")
    
    else:
        print(f"\n❌ SCRAPING FAILED!")
        print(f"🌍 If you're in Pakistan, try:")
        print(f"   • Use a VPN (US/Europe server)")
        print(f"   • Increase REQUEST_DELAY")
        print(f"   • Try at different times")
        
    print("\n" + "=" * 60)
    print("🏁 SCRAPER FINISHED")