import streamlit as st
import pandas as pd
from datetime import datetime
import pdfplumber
import io

def parse_dates(time_frame, default_year=2026):
    """Μετατρέπει τα formats ημερομηνίας (π.χ. 25/4-26/4) σε ημερομηνίες συστήματος."""
    time_frame = str(time_frame).strip()
    
    if '-' in time_frame:
        parts = time_frame.split('-')
        start_part = parts[0].strip()
        end_part = parts[1].strip()
        
        if len(end_part.split('/')) == 3:
            end_date = datetime.strptime(end_part, '%d/%m/%Y')
            year = end_date.year
        else:
            end_date = datetime.strptime(f"{end_part}/{default_year}", '%d/%m/%Y')
            year = default_year
            
        start_elements = start_part.split('/')
        start_day = int(start_elements[0])
        start_month = int(start_elements[1])
        
        start_year = year - 1 if start_month > end_date.month else year
        start_date = datetime(start_year, start_month, start_day)
        return start_date, end_date

    return None, None

def generate_ics(df):
    """Δημιουργεί το αρχείο .ics για το ημερολόγιο."""
    ics_content = "BEGIN:VCALENDAR\nVERSION:2.0\nPRODID:-//Villa App//GR\n"
    for index, row in df.iterrows():
        guest = str(row.get('Guest', '')).strip()
        people = str(row.get('People', '')).strip()
        time_frame = str(row.get('Time frame', '')).strip()
        
        # Αγνόησε γραμμές που είναι κενές ή περιέχουν σύνολα ("Total")
        if not guest or guest.lower() == 'nan' or guest.lower() == 'total' or not time_frame or time_frame.lower() == 'nan':
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
            
    ics_content += "END:VCALENDAR"
    return ics_content

# --- Διεπαφή Χρήστη ---
st.set_page_config(page_title="Ενημέρωση Κρατήσεων", page_icon="📅")
st.title("📅 Ενημέρωση Κρατήσεων")
st.write("Ανέβασε το αρχείο (CSV, Excel ή PDF) για να δημιουργήσεις το αρχείο ημερολογίου.")

uploaded_file = st.file_uploader("Επιλέξτε αρχείο", type=["csv", "xlsx", "pdf"])

if uploaded_file is not None:
    df = None
    try:
        if uploaded_file.name.endswith('.csv'):
            df = pd.read_csv(uploaded_file)
        elif uploaded_file.name.endswith('.xlsx'):
            df = pd.read_excel(uploaded_file)
        elif uploaded_file.name.endswith('.pdf'):
            with pdfplumber.open(uploaded_file) as pdf:
                table = pdf.pages[0].extract_table()
                if table:
                    # Η πρώτη γραμμή είναι οι κεφαλίδες
                    df = pd.DataFrame(table[1:], columns=table[0])
    except Exception as e:
        st.error(f"Σφάλμα κατά την ανάγνωση του αρχείου: {e}")

    if df is not None and not df.empty:
        # Καθαρισμός και εμφάνιση
        df = df.dropna(subset=['Guest', 'Time frame'], how='all')
        st.success("Το αρχείο διαβάστηκε με επιτυχία!")
        st.dataframe(df[['Guest', 'Time frame', 'People']].head(10))
        
        # Παραγωγή του αρχείου ημερολογίου
        ics_data = generate_ics(df)
        
        st.write("---")
        st.write("### Το Ημερολόγιο είναι έτοιμο!")
        st.write("Κατέβασε το αρχείο. Στο κινητό σου θα περάσει τις κρατήσεις αυτόματα. Μπορείς επίσης να στείλεις αυτό το αρχείο στους πελάτες/συνεργάτες σου.")
        
        st.download_button(
            label="📲 Λήψη Αρχείου Ημερολογίου (.ics)",
            data=ics_data,
            file_name="kratiseis.ics",
            mime="text/calendar",
            type="primary"
        )