import streamlit as st
import pandas as pd
from datetime import datetime, timedelta
import pdfplumber
import io
import re

def parse_dates(time_frame, default_year=2026):
    """Καθαρίζει τα κενά και μετατρέπει τα formats ημερομηνίας με απόλυτη ασφάλεια."""
    # Αφαιρούμε εντελώς τα κενά αν έχουν μπει κατά λάθος (π.χ. " 25/4 - 26/4 ")
    time_frame = str(time_frame).strip().replace(" ", "")
    
    try:
        # Περίπτωση 1: YYYY-MM-DD
        if re.match(r'^\d{4}-\d{2}-\d{2}', time_frame):
            start = datetime.strptime(time_frame[:10], '%Y-%m-%d')
            return start, start + timedelta(days=1)
            
        # Περίπτωση 2: 25/4-26/4
        if '-' in time_frame:
            parts = time_frame.split('-')
            if len(parts) >= 2:
                start_part = parts[0]
                end_part = parts[1]
                
                if end_part.count('/') == 2:
                    end_date = datetime.strptime(end_part, '%d/%m/%Y')
                else:
                    end_date = datetime.strptime(f"{end_part}/{default_year}", '%d/%m/%Y')
                    
                year = end_date.year
                start_elements = start_part.split('/')
                start_day = int(start_elements[0])
                start_month = int(start_elements[1])
                
                start_year = year - 1 if start_month > end_date.month else year
                start_date = datetime(start_year, start_month, start_day)
                return start_date, end_date
    except Exception:
        # Αν η ημερομηνία δεν βγάζει κανένα νόημα, μην κρασάρεις, απλά προχώρα.
        pass

    return None, None

def generate_ics(df):
    """Δημιουργεί το αρχείο .ics και καταγράφει όσους είχαν άκυρη ημερομηνία."""
    ics_content = "BEGIN:VCALENDAR\nVERSION:2.0\nPRODID:-//Villa App//GR\n"
    skipped_rows = []
    
    for index, row in df.iterrows():
        guest = str(row.get('Guest', '')).strip()
        people = str(row.get('People', '')).strip()
        time_frame = str(row.get('Time frame', '')).strip()
        
        if not guest or guest.lower() in ['nan', 'none'] or 'total' in guest.lower() or not time_frame or time_frame.lower() in ['nan', 'none']:
            continue
            
        start_date, end_date = parse_dates(time_frame)
        
        if start_date and end_date:
            start_str = start_date.strftime('%Y%m%d')
            end_str = end_date.strftime('%Y%m%d')
            
            ics_content += "BEGIN:VEVENT\n"
            ics_content += f"DTSTART;VALUE=DATE:{start_str}\n"
            ics_content += f"DTEND;VALUE=DATE:{end_str}\n"
            ics_content += f"SUMMARY:🏠 Κράτηση: {guest}\n"
            ics_content += f"DESCRIPTION:Άτομα: {people}\n"
            ics_content += "END:VEVENT\n"
        else:
            skipped_rows.append(f"{guest} (Ημερομηνία: {time_frame})")
            
    ics_content += "END:VCALENDAR"
    return ics_content, skipped_rows

def fix_dataframe_headers(df):
    df.columns = df.columns.astype(str).str.strip().str.replace('\n', '')
    if 'Guest' in df.columns and 'Time frame' in df.columns:
        return df
        
    for i, row in df.head(10).iterrows():
        row_strs = row.astype(str).str.strip().str.replace('\n', '')
        if 'Guest' in row_strs.values and 'Time frame' in row_strs.values:
            df.columns = row_strs
            return df.iloc[i+1:].reset_index(drop=True)
    return df

# --- Διεπαφή Χρήστη ---
st.set_page_config(page_title="Ενημέρωση Κρατήσεων", page_icon="📅")
st.title("📅 Ενημέρωση Κρατήσεων")
st.write("Ανέβασε το αρχείο (CSV, Excel ή PDF) για να δημιουργήσεις το αρχείο ημερολογίου.")

uploaded_file = st.file_uploader("Επιλέξτε αρχείο", type=["csv", "xlsx", "pdf"])

if uploaded_file is not None:
    df = None
    try:
        if uploaded_file.name.endswith('.csv'):
            df = pd.read_csv(uploaded_file, sep=None, engine='python')
        elif uploaded_file.name.endswith('.xlsx'):
            df = pd.read_excel(uploaded_file)
        elif uploaded_file.name.endswith('.pdf'):
            with pdfplumber.open(uploaded_file) as pdf:
                table = pdf.pages[0].extract_table()
                if table:
                    df = pd.DataFrame(table[1:], columns=table[0])
    except Exception as e:
        st.error(f"Σφάλμα κατά την ανάγνωση του αρχείου: {e}")

    if df is not None and not df.empty:
        df = fix_dataframe_headers(df)
        
        if 'Guest' in df.columns and 'Time frame' in df.columns:
            df = df.dropna(subset=['Guest', 'Time frame'], how='all')
            st.success("Το αρχείο διαβάστηκε με επιτυχία!")
            
            # Δείχνει όλη τη λίστα, όχι μόνο 10
            st.dataframe(df[['Guest', 'Time frame', 'People']])
            
            ics_data, skipped = generate_ics(df)
            
            st.write("---")
            if skipped:
                st.warning("⚠️ ΠΡΟΣΟΧΗ: Οι παρακάτω κρατήσεις δεν μπήκαν στο ημερολόγιο επειδή η ημερομηνία τους δεν είναι σε μορφή π.χ. 25/4-26/4 :")
                for s in skipped:
                    st.write(f"- {s}")
                    
            st.write("### Το Ημερολόγιο είναι έτοιμο!")
            st.write("Κατέβασε το αρχείο. Στο iPhone θα περάσει τις κρατήσεις αυτόματα.")
            
            st.download_button(
                label="📲 Λήψη Αρχείου Ημερολογίου (.ics)",
                data=ics_data,
                file_name="kratiseis.ics",
                mime="text/calendar",
                type="primary"
            )
        else:
            st.error("Δεν βρέθηκαν οι στήλες 'Guest' και 'Time frame'.")
