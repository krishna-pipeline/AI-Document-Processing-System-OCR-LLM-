import os
import re
import requests
import json
from fpdf import FPDF
from datetime import datetime, date

# =========================================================
# BASE DIRECTORY SETUP
# =========================================================
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
OUTPUT_DIR = os.path.join(BASE_DIR, 'extracted_text')

DOCUMENT_TYPES = {
    'policy_copy': os.path.join(OUTPUT_DIR, 'policy_copy'),
    'discharge_summary': os.path.join(OUTPUT_DIR, 'discharge_summary'),
    'rejection_letter': os.path.join(OUTPUT_DIR, 'rejection_letter')
}

# =========================================================
# LOCAL LLM CONFIGURATION
# =========================================================
LOCAL_LLM_CONFIG = {
    'url': 'http://localhost:11434/api/generate',
    'model': 'gemma3:12b',
    'timeout': 600
}

# =========================================================
# FIELD DEFINITIONS FOR EACH DOCUMENT TYPE
# =========================================================
FIELD_DEFINITIONS = {
    'policy_copy': {
        'Policy_Number': 'Insurance policy number. Extract exactly as printed.',

        'Policy_Holder_Name': 'Full name of the policy holder exactly as printed.',

        'Policy_Holder_Address': 'Complete address of the policy holder including city, state and pincode. If not found use "Not Found".',

        'Date_of_Birth': 'Date of birth of policy holder in DD/MM/YYYY format. If not found use "Not Found".',

        'Gender': 'Gender of policy holder. Extract as Male, Female or Other. If not found use "Not Found".',

        'Product_Plan_Name': 'Name of the insurance product or plan. Example: Activ One NXT, Care Advantage, Optima Restore. If not found use "Not Found".',

        'Coverage_Amount': 'Total sum insured or coverage amount. Extract the COMPLETE number exactly as printed including all digits. Indian format examples: 10,00,000 or 25,00,000 or 5,00,000. Do NOT truncate, round, or drop any digits. Do NOT convert format. If not found use "Not Found".',

        'Policy_Inception_Date': 'The date the policy was FIRST EVER issued or originated. This is the ORIGINAL start date of the policy from day one, NOT the current renewal date. If the policy has been renewed multiple times, this is still the very first date. In DD/MM/YYYY format. If not found use "Not Found".',

        'Policy_Period_Start_Date': 'Start date of the CURRENT active policy term or renewal period only. This is different from inception date. In DD/MM/YYYY format. If not found use "Not Found".',

        'Policy_Period_End_Date': 'End date of the current active policy term. In DD/MM/YYYY format. If not found use "Not Found".',

        'Premium_Amount': 'Premium amount paid for the current policy term. Extract exact figure as printed. If not found use "Not Found".',

        'Insurance_Company': 'Full name of the insurance company exactly as printed.',

        'TPA_Name': 'Name of the Third Party Administrator if mentioned anywhere in the document. If not found use "Not Found".',

        'Previous_Insurer_Name': 'Name of previous insurance company if this is a ported policy. If not found use "Not Found".',

        'Pre_Existing_Disease_Waiting_Period': 'Waiting period applicable for pre-existing diseases as stated in policy. Extract exact duration as mentioned example: 2 Years, 48 Months, 4 Years. If not found use "Not Found".',

        'Specific_Disease_Waiting_Period': 'Any specific disease waiting periods mentioned separately from the general PED waiting period. Extract disease name and duration together. Example: Diabetes - 2 Years; Hypertension - 2 Years; Cardiac conditions - 4 Years. If not found use "Not Found".',

        'All_Declared_PED': 'A flat combined summary of ALL pre-existing diseases declared across ALL members in the policy. If multiple conditions separate with semicolons. If the document explicitly states no pre-existing diseases use "None Declared". If the document does not mention pre-existing diseases at all use "Not Found".',

        'Member_wise_PED': '''Extract pre-existing disease details for EACH member covered under this policy as a JSON array.
Each member must be a separate object in the array with these exact keys:
- "Member_Name": Full name of the member
- "Relation": Relationship to policy holder (Self, Spouse, Son, Daughter, Father, Mother)
- "Pre_Existing_Diseases": Pre-existing diseases declared for this member. If none use "None Declared"
- "Waiting_Period": Waiting period applicable for this member pre-existing diseases as stated in policy. If not found use "Not Found"

IMPORTANT RULES:
- Even if only one member exists return an array with one object
- Extract ONLY members and conditions explicitly mentioned in the document
- Do NOT invent members or conditions not present in the document
- If no member wise PED information found return an empty array []

Example format:
[{"Member_Name": "John Doe", "Relation": "Self", "Pre_Existing_Diseases": "Hypertension", "Waiting_Period": "2 Years"},
{"Member_Name": "Jane Doe", "Relation": "Spouse", "Pre_Existing_Diseases": "Diabetes Mellitus", "Waiting_Period": "2 Years"}]'''
    },

    'discharge_summary': {
        'Patient_Name': 'Full name of the patient exactly as printed.',

        'Patient_ID': 'Patient identification or registration number. If not found use "Not Found".',

        'Date_of_Admission': 'Date patient was admitted to hospital in DD/MM/YYYY format. If not found use "Not Found".',

        'Date_of_Discharge': 'Date patient was discharged from hospital in DD/MM/YYYY format. If not found use "Not Found".',

        'Primary_Diagnosis': 'Main or primary diagnosis exactly as stated in the document. If not found use "Not Found".',

        'Secondary_Diagnosis': 'Any secondary or additional diagnoses mentioned alongside the primary diagnosis. If multiple separate with semicolons. If none mentioned use "Not Found".',

        'Procedures_Performed': 'All medical procedures or surgeries performed during the hospital stay. If multiple separate with semicolons. If not found use "Not Found".',

        'Doctor_Name': 'Name of the primary attending or treating doctor. If not found use "Not Found".',

        'Hospital_Name': 'Full name of the hospital exactly as printed.',

        'Known_Case_Of': 'All conditions listed under K/C/O or Known Case Of section ONLY. Extract ONLY what is explicitly written under this section. If multiple conditions separate with semicolons. If none mentioned use "Not Found".',

        'Known_Condition_Duration': '''Duration of each known condition as EXPLICITLY stated in the document.
Extract as condition name paired with duration exactly as written.
Example: Hypertension - 3 years; Diabetes - 5 years
IMPORTANT:
- Extract ONLY durations explicitly mentioned in the document
- Do NOT assume or calculate durations
- If duration is mentioned for some conditions but not others extract what is available and use "duration not stated" for the rest
- If no durations mentioned anywhere use "Not Found"''',

        'Final_Bill_Amount': 'Total final bill amount charged by the hospital. Extract COMPLETE figure exactly as printed including all digits. Indian format examples: 5,45,729 or 6,59,110. Do NOT truncate or round. If not found use "Not Found".',
    },

    'rejection_letter': {
        'Claim_Number': 'Insurance claim number exactly as printed.',

        'Patient_Name': 'Full name of the patient exactly as printed.',

        'Policy_Number': 'Policy number exactly as printed.',

        'Claim_Intimation_Date': 'Date the claim was first intimated or filed by the patient or hospital. In DD/MM/YYYY format. If not found use "Not Found".',

        'Rejection_Date': 'Date the claim was formally rejected by the insurance company. In DD/MM/YYYY format. If not found use "Not Found".',

        'Specific_Clause_Numbers': 'All clause numbers, section numbers or code references cited as basis for rejection. Extract ONLY the numbers or codes. Example: 5.1.6; Clause 4.2; Section 3.1. Separate multiple with semicolons. If not found use "Not Found".',

        'Rejection_Reasons': '''Complete rejection reasons exactly as stated in the document.
IMPORTANT RULES:
- Preserve the ORIGINAL wording from the document exactly
- Include both clause codes and full explanation text for each reason
- If multiple reasons exist separate them with semicolons
- Do NOT summarize or paraphrase
- Do NOT jam words together - if OCR has caused words to be joined add a space between them
- If not found use "Not Found"''',

        'Hospital_Name': 'Name of hospital where treatment was taken. If not found use "Not Found".',

        'Insurance_Company': 'Full name of the insurance company exactly as printed.',

        'TPA_Name': 'Name of Third Party Administrator handling the claim. If not found use "Not Found".',
    }
}


# =========================================================
# CHECK LOCAL LLM CONNECTION
# =========================================================
def check_local_llm():
    """Check if Ollama is running and model is available"""
    try:
        response = requests.post(
            LOCAL_LLM_CONFIG['url'],
            json={'model': LOCAL_LLM_CONFIG['model'], 'prompt': 'test'},
            timeout=10
        )
        if response.status_code == 200:
            print(f"✓ Ollama connected: {LOCAL_LLM_CONFIG['model']}")
            return True
        else:
            print(f"  Ollama error: Status {response.status_code}")
            return False
    except Exception as e:
        print(f"  Ollama not reachable: {e}")
        return False


# =========================================================
# GENERATE EXTRACTION PROMPT
# =========================================================
def get_strict_extraction_prompt(document_type, ocr_text, fields):
    """Generate prompt for LLM extraction"""
    if len(ocr_text) > 15000:
        ocr_text = ocr_text[:10000] + "\n\n[...TEXT TRUNCATED...]\n\n" + ocr_text[-5000:]

    field_list = "\n".join([f"- {k}: {v}" for k, v in fields.items()])

    prompt = f"""<|begin_of_text|><|start_header_id|>system<|end_header_id|>
You are a medical document data extractor. Extract the requested fields from the provided document.

FIELDS TO EXTRACT:
{field_list}

CRITICAL RULES - READ CAREFULLY:
- Extract information ONLY from the document provided below
- Do NOT invent, assume, or fabricate any data
- Do NOT use placeholder, example, or dummy data
- If a field is not explicitly mentioned in the document you MUST use "Not Found"
- For amounts and bills: Extract ONLY the exact figures mentioned in the document
- INDIAN NUMBER FORMAT: Amounts are written as 10,00,000 or 25,00,000 or 5,45,729 — extract the COMPLETE number exactly as printed, do NOT drop digits, do NOT truncate after first comma
- For K/C/O Known Case Of: Extract ONLY diseases or conditions explicitly stated in the document
- For Pre-existing diseases: Extract ONLY what is explicitly listed in the policy document
- Dates must be in DD/MM/YYYY format
- JAMMED TEXT: If OCR has joined words together like DISCREPANCYINMEDICALDOCUMENTS add spaces between words like DISCREPANCY IN MEDICAL DOCUMENTS
- For Member_wise_PED: Return a valid JSON array of objects inside the main JSON — NOT a string
- For Rejection_Reasons: Extract complete information including all codes and explanations separated by semicolons
- Return ONLY a valid JSON object with double quotes around all keys and string values
- Member_wise_PED must be a JSON array not a string
- Do not include any text before or after the JSON object
- Do not make assumptions or use general medical knowledge to fill in fields

STRICTLY FORBIDDEN:
- Making up data not present in the document
- Using example values or templates
- Inferring information not explicitly stated
- Adding explanatory text outside the JSON
- Truncating Indian number format amounts

<|eot_id|><|start_header_id|>user<|end_header_id|>

DOCUMENT TYPE: {document_type}

DOCUMENT TEXT:
{ocr_text}

Return the extracted data as a JSON object:

<|eot_id|><|start_header_id|>assistant<|end_header_id|>
{{"""

    return prompt


# =========================================================
# POST PROCESS FIELDS
# =========================================================
def post_process_fields(document_type, result):
    """Compute derived fields after LLM extraction"""

    # ── POLICY COPY ──────────────────────────────────────
    if document_type == 'policy_copy':

        # Compute Age from Date_of_Birth
        dob_str = result.get('Date_of_Birth', 'Not Found')
        if dob_str and dob_str != 'Not Found':
            try:
                # Handle both DD/MM/YYYY and DD-MM-YYYY formats
                dob_str_clean = dob_str.replace('-', '/')
                dob = datetime.strptime(dob_str_clean, '%d/%m/%Y')
                today = date.today()
                age = today.year - dob.year - (
                    (today.month, today.day) < (dob.month, dob.day)
                )
                result['Age'] = str(age)
            except Exception:
                result['Age'] = 'Not Computed'
        else:
            result['Age'] = 'Not Found'

        # Parse Member_wise_PED — if LLM returned it as string try to parse
        member_ped = result.get('Member_wise_PED', [])
        if isinstance(member_ped, str):
            try:
                parsed = json.loads(member_ped)
                result['Member_wise_PED'] = parsed
            except Exception:
                # Keep as string — PDF renderer will handle gracefully
                print("  ⚠ Member_wise_PED could not be parsed as JSON array")

        # Compute Waiting_Period_Expiry per member
        inception_str = result.get('Policy_Inception_Date', 'Not Found')
        if inception_str and inception_str != 'Not Found':
            try:
                inception_str_clean = inception_str.replace('-', '/')
                inception_date = datetime.strptime(inception_str_clean, '%d/%m/%Y')

                members = result.get('Member_wise_PED', [])
                if isinstance(members, list):
                    for member in members:
                        wp = member.get('Waiting_Period', 'Not Found')
                        if wp and wp != 'Not Found':
                            try:
                                # Extract number from waiting period string
                                # Handles: "2 Years", "48 Months", "4 Years"
                                wp_lower = wp.lower()
                                numbers = re.findall(r'\d+', wp_lower)
                                if numbers:
                                    wp_num = int(numbers[0])
                                    if 'month' in wp_lower:
                                        from dateutil.relativedelta import relativedelta
                                        expiry = inception_date + relativedelta(months=wp_num)
                                    else:
                                        from dateutil.relativedelta import relativedelta
                                        expiry = inception_date + relativedelta(years=wp_num)
                                    member['Waiting_Period_Expiry'] = expiry.strftime('%d/%m/%Y')
                                else:
                                    member['Waiting_Period_Expiry'] = 'Not Computed'
                            except Exception:
                                member['Waiting_Period_Expiry'] = 'Not Computed'
                        else:
                            member['Waiting_Period_Expiry'] = 'Not Computed'
            except Exception:
                print("  ⚠ Could not compute Waiting_Period_Expiry — check Policy_Inception_Date format")

        # Validate Coverage_Amount — sanity check for Indian format issues
        coverage = result.get('Coverage_Amount', 'Not Found')
        if coverage and coverage != 'Not Found':
            try:
                # Remove commas and check if number is suspiciously small
                clean_coverage = coverage.replace(',', '').replace('Rs', '').replace('₹', '').strip()
                coverage_num = float(clean_coverage)
                if coverage_num < 10000:
                    result['Coverage_Amount'] = f"{coverage} — VERIFY MANUALLY (possible extraction error)"
            except Exception:
                pass

    # ── DISCHARGE SUMMARY ────────────────────────────────
    elif document_type == 'discharge_summary':

        # Compute Length of Stay
        admission_str = result.get('Date_of_Admission', 'Not Found')
        discharge_str = result.get('Date_of_Discharge', 'Not Found')

        if (admission_str and admission_str != 'Not Found' and
                discharge_str and discharge_str != 'Not Found'):
            try:
                admission_str_clean = admission_str.replace('-', '/')
                discharge_str_clean = discharge_str.replace('-', '/')
                admission = datetime.strptime(admission_str_clean, '%d/%m/%Y')
                discharge = datetime.strptime(discharge_str_clean, '%d/%m/%Y')
                los = (discharge - admission).days
                result['Length_of_Stay'] = f"{los} day{'s' if los != 1 else ''}"
            except Exception:
                result['Length_of_Stay'] = 'Not Computed'
        else:
            result['Length_of_Stay'] = 'Not Found'

    return result


# =========================================================
# EXTRACT FIELDS WITH LOCAL LLM
# =========================================================
def extract_fields_with_local_llm(document_type, ocr_text):
    """Extract structured fields from OCR text using local LLM"""
    res_text = ""
    try:
        if document_type not in FIELD_DEFINITIONS:
            print(f"  Unknown document type: {document_type}")
            return None

        fields = FIELD_DEFINITIONS[document_type]
        prompt = get_strict_extraction_prompt(document_type, ocr_text, fields)

        payload = {
            "model": LOCAL_LLM_CONFIG['model'],
            "prompt": prompt,
            "stream": False,
            "options": {
                "temperature": 0,
                "num_ctx": 8192
            }
        }

        print(f"    Sending to {LOCAL_LLM_CONFIG['model']}")
        response = requests.post(
            LOCAL_LLM_CONFIG['url'],
            json=payload,
            timeout=LOCAL_LLM_CONFIG['timeout']
        )

        if response.status_code == 200:
            res_text = response.json().get('response', '').strip()

            # DEBUG: Show raw response
            print(f"\n    RAW LLM RESPONSE (first 300 chars):")
            print(f"   {'-' * 60}")
            print(f"   {res_text[:300]}")
            print(f"   {'-' * 60}\n")

            # Clean up response
            res_text = re.sub(r'```json\s*', '', res_text)
            res_text = re.sub(r'```\s*', '', res_text)
            res_text = res_text.strip()

            # Find JSON object boundaries
            start_idx = res_text.find('{')
            end_idx = res_text.rfind('}')

            if start_idx != -1 and end_idx != -1:
                res_text = res_text[start_idx:end_idx + 1]

            # DEBUG: Show cleaned response
            print(f"   CLEANED RESPONSE (first 300 chars):")
            print(f"   {'-' * 60}")
            print(f"   {res_text[:300]}")
            print(f"   {'-' * 60}\n")

            # Parse JSON
            data = json.loads(res_text)

            # Ensure all fields present
            result = {k: data.get(k, "Not Found") for k in fields.keys()}

            # Debug for rejection letter
            if document_type == 'rejection_letter':
                print(f"\n    DEBUG - Full Rejection Reasons:")
                print(f"   {result.get('Rejection_Reasons', 'N/A')}\n")

            # ── POST PROCESS ──────────────────────────────
            result = post_process_fields(document_type, result)

            print(f"   ✓ Extracted and processed {len(result)} fields")
            return result

        else:
            print(f"    LLM returned status {response.status_code}")
            return None

    except json.JSONDecodeError as e:
        print(f"    JSON parsing error: {e}")
        print(f"   ⚠  Full response length: {len(res_text)} chars")
        print(f"   ⚠  Response preview (first 500 chars):")
        print(f"   {res_text[:500]}")

        error_file = os.path.join(BASE_DIR, f'error_{document_type}.txt')
        with open(error_file, 'w', encoding='utf-8') as f:
            f.write(res_text)
        print(f"    Full response saved to: {error_file}")
        return None

    except Exception as e:
        print(f"    LLM Error for {document_type}: {e}")
        import traceback
        traceback.print_exc()
        return None


# =========================================================
# PDF HELPER FUNCTIONS
# =========================================================
def sanitize(text):
    """Remove non-latin characters that FPDF cannot render"""
    return str(text).encode('latin-1', 'replace').decode('latin-1')


def render_section_header(pdf, title):
    """Render a colored section header"""
    pdf.set_font('Arial', 'B', 10)
    pdf.set_fill_color(30, 80, 160)
    pdf.set_text_color(255, 255, 255)
    pdf.cell(0, 7, f'  {title}', 0, 1, 'L', True)
    pdf.set_text_color(0, 0, 0)
    pdf.ln(2)


def render_field_row(pdf, label, value):
    """Render a single label value row with proper wrapping"""
    label_width = 70
    value_width = 115

    value_str = sanitize(str(value)) if value else 'Not Found'
    label_str = sanitize(label + ':')

    # Calculate height needed
    pdf.set_font('Arial', '', 8)
    lines = pdf.multi_cell(value_width, 4, value_str, border=0,
                           align='L', split_only=True)
    row_height = max(5, len(lines) * 4 + 2)

    y_start = pdf.get_y()

    # Page break check
    if y_start + row_height > pdf.page_break_trigger:
        pdf.add_page()
        y_start = pdf.get_y()

    # Render label
    pdf.set_font('Arial', 'B', 8)
    pdf.set_xy(10, y_start)
    pdf.multi_cell(label_width, row_height, label_str, border=0, align='L')

    # Render value
    pdf.set_font('Arial', '', 8)
    pdf.set_xy(10 + label_width, y_start)
    pdf.multi_cell(value_width, 4, value_str, border=0, align='L')

    pdf.set_y(y_start + row_height)
    pdf.ln(1)


def render_member_ped_table(pdf, members):
    """Render Member_wise_PED as a clean table"""
    if not members:
        render_field_row(pdf, 'Member Wise PED', 'Not Found')
        return

    # Section label
    pdf.set_font('Arial', 'B', 8)
    pdf.cell(0, 5, 'Member Wise PED Details:', 0, 1)
    pdf.ln(1)

    # Column widths
    col_widths = [50, 22, 55, 28, 30]
    headers = ['Member Name', 'Relation', 'Pre Existing Diseases',
               'Waiting Period', 'Expiry Date']

    # Table header
    pdf.set_font('Arial', 'B', 7)
    pdf.set_fill_color(30, 80, 160)
    pdf.set_text_color(255, 255, 255)
    for i, header in enumerate(headers):
        pdf.cell(col_widths[i], 6, f' {header}', 1, 0, 'L', True)
    pdf.ln()
    pdf.set_text_color(0, 0, 0)

    # Table rows
    pdf.set_font('Arial', '', 7)
    for idx, member in enumerate(members):
        if idx % 2 == 0:
            pdf.set_fill_color(245, 248, 255)
        else:
            pdf.set_fill_color(255, 255, 255)

        name    = sanitize(member.get('Member_Name', 'Not Found'))
        relation= sanitize(member.get('Relation', 'Not Found'))
        ped     = sanitize(member.get('Pre_Existing_Diseases', 'Not Found'))
        waiting = sanitize(member.get('Waiting_Period', 'Not Found'))
        expiry  = sanitize(member.get('Waiting_Period_Expiry', 'Not Computed'))

        values = [name, relation, ped, waiting, expiry]

        # Calculate row height
        max_lines = 1
        for i, val in enumerate(values):
            lines = pdf.multi_cell(col_widths[i], 4, val, border=0,
                                   align='L', split_only=True)
            max_lines = max(max_lines, len(lines))
        row_h = max_lines * 4 + 2

        # Page break check
        if pdf.get_y() + row_h > pdf.page_break_trigger:
            pdf.add_page()

        y_row = pdf.get_y()
        x_start = 10
        for i, val in enumerate(values):
            pdf.set_xy(x_start + sum(col_widths[:i]), y_row)
            pdf.multi_cell(col_widths[i], row_h, f' {val}',
                           border=1, align='L', fill=True)

        pdf.set_y(y_row + row_h)

    pdf.ln(3)


# =========================================================
# CREATE COMBINED SUMMARY PDF
# =========================================================
def create_combined_summary_pdf(all_data):
    """Generate clean four bucket PDF report from extracted JSON"""

    class PDF(FPDF):
        def header(self):
            self.set_font('Arial', 'B', 13)
            self.set_text_color(30, 80, 160)
            self.cell(0, 8, 'Health Claim Analysis Report', 0, 1, 'C')
            self.set_font('Arial', 'I', 8)
            self.set_text_color(120, 120, 120)
            self.cell(0, 4,
                f'Generated: {datetime.now().strftime("%d %b %Y %H:%M")}  |  For Adjudicator Review',
                0, 1, 'C')
            self.set_text_color(0, 0, 0)
            self.ln(3)

        def footer(self):
            self.set_y(-10)
            self.set_font('Arial', 'I', 7)
            self.set_text_color(150, 150, 150)
            self.cell(0, 5,
                f'Page {self.page_no()}  |  AI extraction only - human adjudicator has final authority',
                0, 0, 'C')

    pdf = PDF()
    pdf.set_auto_page_break(auto=True, margin=15)
    pdf.add_page()

    # ─────────────────────────────────────────────────────
    # BUCKET 1 — INSURANCE POLICY DETAILS
    # ─────────────────────────────────────────────────────
    if 'policy_copy' in all_data:
        render_section_header(pdf, 'BUCKET 1 - INSURANCE POLICY DETAILS')
        data = all_data['policy_copy']

        flat_fields = [
            ('Policy Number',                    'Policy_Number'),
            ('Policy Holder Name',               'Policy_Holder_Name'),
            ('Policy Holder Address',            'Policy_Holder_Address'),
            ('Date of Birth',                    'Date_of_Birth'),
            ('Age',                              'Age'),
            ('Gender',                           'Gender'),
            ('Insurance Company',                'Insurance_Company'),
            ('Product Plan Name',                'Product_Plan_Name'),
            ('TPA Name',                         'TPA_Name'),
            ('Previous Insurer Name',            'Previous_Insurer_Name'),
            ('Coverage Amount',                  'Coverage_Amount'),
            ('Premium Amount',                   'Premium_Amount'),
            ('Policy Inception Date',            'Policy_Inception_Date'),
            ('Policy Period Start Date',         'Policy_Period_Start_Date'),
            ('Policy Period End Date',           'Policy_Period_End_Date'),
            ('PED Waiting Period',               'Pre_Existing_Disease_Waiting_Period'),
            ('Specific Disease Waiting Period',  'Specific_Disease_Waiting_Period'),
            ('All Declared PED',                 'All_Declared_PED'),
        ]

        for label, key in flat_fields:
            render_field_row(pdf, label, data.get(key, 'Not Found'))

        # Member wise PED table
        pdf.ln(2)
        member_ped = data.get('Member_wise_PED', [])
        if isinstance(member_ped, str):
            render_field_row(pdf, 'Member Wise PED', member_ped)
        else:
            render_member_ped_table(pdf, member_ped)

        pdf.ln(4)

    # ─────────────────────────────────────────────────────
    # BUCKET 2 — HOSPITAL DISCHARGE SUMMARY
    # ─────────────────────────────────────────────────────
    if 'discharge_summary' in all_data:
        render_section_header(pdf, 'BUCKET 2 - HOSPITAL DISCHARGE SUMMARY')
        data = all_data['discharge_summary']

        discharge_fields = [
            ('Patient Name',             'Patient_Name'),
            ('Patient ID',               'Patient_ID'),
            ('Hospital Name',            'Hospital_Name'),
            ('Doctor Name',              'Doctor_Name'),
            ('Date of Admission',        'Date_of_Admission'),
            ('Date of Discharge',        'Date_of_Discharge'),
            ('Length of Stay',           'Length_of_Stay'),
            ('Primary Diagnosis',        'Primary_Diagnosis'),
            ('Secondary Diagnosis',      'Secondary_Diagnosis'),
            ('Procedures Performed',     'Procedures_Performed'),
            ('Known Case Of',            'Known_Case_Of'),
            ('Known Condition Duration', 'Known_Condition_Duration'),
            ('Final Bill Amount',        'Final_Bill_Amount'),
        ]

        for label, key in discharge_fields:
            render_field_row(pdf, label, data.get(key, 'Not Found'))

        pdf.ln(4)

    # ─────────────────────────────────────────────────────
    # BUCKET 3 — DECLARED VS FOUND
    # ─────────────────────────────────────────────────────
    if 'policy_copy' in all_data and 'discharge_summary' in all_data:
        render_section_header(pdf, 'BUCKET 3 - DECLARED VS FOUND')

        policy  = all_data['policy_copy']
        discharge = all_data['discharge_summary']

        render_field_row(pdf, 'PED Declared at Proposal',
                         policy.get('All_Declared_PED', 'Not Found'))
        render_field_row(pdf, 'Conditions Found at Discharge',
                         discharge.get('Known_Case_Of', 'Not Found'))
        render_field_row(pdf, 'Duration of Known Conditions',
                         discharge.get('Known_Condition_Duration', 'Not Found'))
        render_field_row(pdf, 'Policy Inception Date',
                         policy.get('Policy_Inception_Date', 'Not Found'))
        render_field_row(pdf, 'PED Waiting Period',
                         policy.get('Pre_Existing_Disease_Waiting_Period', 'Not Found'))
        render_field_row(pdf, 'Date of Admission',
                         discharge.get('Date_of_Admission', 'Not Found'))

        pdf.ln(4)

    # ─────────────────────────────────────────────────────
    # BUCKET 4 — CLAIM REJECTION DETAILS
    # ─────────────────────────────────────────────────────
    if 'rejection_letter' in all_data:
        render_section_header(pdf, 'BUCKET 4 - CLAIM REJECTION DETAILS')
        data = all_data['rejection_letter']

        rejection_fields = [
            ('Claim Number',             'Claim_Number'),
            ('Patient Name',             'Patient_Name'),
            ('Policy Number',            'Policy_Number'),
            ('Insurance Company',        'Insurance_Company'),
            ('TPA Name',                 'TPA_Name'),
            ('Hospital Name',            'Hospital_Name'),
            ('Claim Intimation Date',    'Claim_Intimation_Date'),
            ('Rejection Date',           'Rejection_Date'),
            ('Specific Clause Numbers',  'Specific_Clause_Numbers'),
            ('Rejection Reasons',        'Rejection_Reasons'),
        ]

        for label, key in rejection_fields:
            render_field_row(pdf, label, data.get(key, 'Not Found'))

        pdf.ln(4)

    # Save PDF
    output_path = os.path.join(BASE_DIR, 'combined_summary.pdf')
    pdf.output(output_path)
    print(f'\n✓ PDF Report created: {output_path}')
    return output_path


# =========================================================
# PROCESS ALL EXTRACTIONS
# =========================================================
def process_all_extractions():
    """Main function to process all document types with LLM"""
    print("\n" + "=" * 60)
    print("PHASE 2: LLM EXTRACTION")
    print("=" * 60)

    all_data = {}

    for doc_type, folder in DOCUMENT_TYPES.items():
        print(f"\n  Processing {doc_type.replace('_', ' ').title()}...")

        if not os.path.exists(folder):
            print(f"    Folder not found: {folder}")
            continue

        files = [f for f in os.listdir(folder) if f.endswith('.txt')]

        if not files:
            print(f"    No text files found in {folder}")
            continue

        text_file = os.path.join(folder, files[0])
        print(f"    Reading: {files[0]}")

        with open(text_file, 'r', encoding='utf-8') as f:
            text = f.read()

        print(f"    Text length: {len(text)} characters")

        # Extract with LLM — post processing happens inside
        result = extract_fields_with_local_llm(doc_type, text)

        if result:
            all_data[doc_type] = result

            # Save JSON — includes computed fields from post processing
            json_path = os.path.join(folder, f"{doc_type}_extracted.json")
            with open(json_path, 'w', encoding='utf-8') as f:
                json.dump(result, f, indent=2)
            print(f"    ✓ JSON saved: {json_path}")

    if all_data:
        pdf_path = create_combined_summary_pdf(all_data)
        return {
            'combined_data': all_data,
            'pdf_path': pdf_path
        }
    else:
        print("\n  No data extracted from any document")
        return {}


# =========================================================
# STANDALONE TEST
# =========================================================
if __name__ == "__main__":
    if check_local_llm():
        results = process_all_extractions()
        if results:
            print("\n✓ Extraction completed successfully!")
        else:
            print("\n  Extraction failed")
    else:
        print("\n  Please start Ollama first: ollama serve")