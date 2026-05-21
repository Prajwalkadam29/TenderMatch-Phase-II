"""
create_fixture_pdf.py
---------------------
Run this once to generate backend/tests/fixtures/sample_vendor_doc.pdf
using PyMuPDF (already a project dependency).
"""
import fitz
import os

def create_sample_vendor_pdf(output_path: str) -> None:
    doc = fitz.open()
    page = doc.new_page(width=595, height=842)  # A4

    content = """
TechCorp Solutions Private Limited
Company Profile & Capability Statement

CIN: U72200MH2010PTC206789
GSTIN: 27AAACT1234A1Z5
PAN: AAACT1234A
Year of Incorporation: 2010
Registered State: Maharashtra
Registered City: Mumbai

BUSINESS OVERVIEW
TechCorp Solutions is a leading IT services and software development company
specializing in enterprise software solutions, cloud infrastructure, and
cybersecurity services. We serve government and private sector clients across India.

FINANCIAL HIGHLIGHTS
Average Annual Turnover: INR 5 Crore
Net Worth: INR 2.5 Crore
Turnover FY 2022-23: Rs. 6 Crore
Turnover FY 2021-22: Rs. 4.5 Crore
Turnover FY 2020-21: Rs. 4 Crore

PRIMARY DOMAINS
- Information Technology Services
- Software Development
- Cloud Infrastructure
- Cybersecurity

CERTIFICATIONS
- ISO 9001:2015 Quality Management System (Valid until Dec 2025)
- ISO 27001:2013 Information Security Management
- CMMI Level 3 Certified

PAST PROJECTS
Project: State Government ERP Implementation
Client: Maharashtra State Government
Client Type: Government
Contract Value: INR 2 Crore
Year of Completion: 2022
Location: Maharashtra
Work Type: Software Development

Project: Smart City Dashboard
Client: Pune Municipal Corporation
Client Type: Municipal
Contract Value: INR 75 Lakhs
Year of Completion: 2023
Location: Maharashtra
Work Type: Web Application Development

MSME Registration: UDYAM-MH-10-0012345
MSME Category: Micro

Total Projects Completed: 47
Years in Business: 13

Blacklisting/Debarment Status: Not Blacklisted
"""

    page.insert_text(
        (50, 50),
        content.strip(),
        fontsize=9,
        fontname="helv",
    )

    doc.save(output_path)
    doc.close()
    print(f"Created fixture PDF: {output_path}")


if __name__ == "__main__":
    here = os.path.dirname(os.path.abspath(__file__))
    out = os.path.join(here, "sample_vendor_doc.pdf")
    create_sample_vendor_pdf(out)
