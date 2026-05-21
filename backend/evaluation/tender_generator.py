"""
tender_generator.py
Generates exactly 50 realistic Indian government/enterprise tenders across 10 domains
with varying difficulty thresholds (low, medium, high) for empirical evaluation.
"""
import json
import os
import random
from datetime import datetime, timedelta

DOMAINS = [
    {"code": "CIVIL", "name": "Civil & Construction", "count": 9},
    {"code": "IT", "name": "IT & Software", "count": 8},
    {"code": "RENEWABLE", "name": "Renewable Energy", "count": 7},
    {"code": "HEALTHCARE", "name": "Healthcare & Medical", "count": 6},
    {"code": "WATER", "name": "Water & Sanitation", "count": 5},
    {"code": "ELECTRICAL", "name": "Electrical & Instrumentation", "count": 5},
    {"code": "ROADS", "name": "Roads & Highways", "count": 4},
    {"code": "SUPPLY", "name": "Supply & Procurement", "count": 3},
    {"code": "CONSULTANCY", "name": "Consultancy & Advisory", "count": 2},
    {"code": "TELECOM", "name": "Telecom & Networking", "count": 1},
]

STATES = ["Maharashtra", "Karnataka", "Delhi", "Gujarat", "Tamil Nadu", "Uttar Pradesh", "Telangana", "Haryana", "Rajasthan"]
PORTALS = ["gem.gov.in", "cppp.nic.in", "etender.up.gov.in", "mahatenders.gov.in", "eproc.karnataka.gov.in"]

# Pre-generate exact difficulty distribution: 15 low, 20 medium, 15 high
difficulties = ["low"] * 15 + ["medium"] * 20 + ["high"] * 15
random.shuffle(difficulties)

def generate_tender(domain_info, seq_num, difficulty):
    domain = domain_info["name"]
    code = domain_info["code"]
    
    # Defaults
    issuer = "Government Department"
    certifications = []
    scope = ""
    title = ""
    
    # Value tuning based on difficulty
    if difficulty == "low":
        val_range = (10_000_00, 50_000_00) # 10L - 50L
        to_range = (5_000_00, 20_000_00)   # 5L - 20L
        exp_range = (1, 3)
    elif difficulty == "medium":
        val_range = (1_000_00_00, 10_000_00_00) # 1Cr - 10Cr
        to_range = (50_000_00, 5_000_00_00)     # 50L - 5Cr
        exp_range = (3, 7)
    else: # high
        val_range = (15_000_00_00, 100_000_00_00) # 15Cr - 100Cr
        to_range = (10_000_00_00, 50_000_00_00)   # 10Cr - 50Cr
        exp_range = (7, 15)
        
    est_value = random.randint(val_range[0], val_range[1])
    min_turnover = random.randint(to_range[0], to_range[1])
    min_exp = random.randint(exp_range[0], exp_range[1])

    if code == "CIVIL":
        issuer = random.choice(["CPWD", "State PWD", "Smart City Corporation"])
        certifications = ["ISO 9001:2015", "CPWD Empanelment"]
        if difficulty == "high": certifications.append("BIS License")
        title = f"Construction of Commercial Complex Phase {seq_num}"
        scope = "Construction of a multi-story commercial complex including civil, structural, and finishing works. The contractor must supply all materials, labor, and machinery. The project includes basic MEP provisions."
    
    elif code == "IT":
        issuer = random.choice(["NIC", "MeitY", "State IT Department", "PSU"])
        certifications = ["ISO 27001", "GEM Registration"]
        if difficulty == "high": certifications.append("CMMI Level 3")
        title = f"Implementation of e-Governance Portal and Data Center Migration v{seq_num}"
        scope = "Design, development, and implementation of a state-wide e-Governance citizen portal. Includes migration of legacy data to a Tier 3 data center. The vendor must provide 3 years of O&M support and cybersecurity audits."
        
    elif code == "RENEWABLE":
        issuer = random.choice(["MNRE", "SECI", "State DISCOM"])
        certifications = ["MNRE Empanelment", "BIS IS 14286"]
        if difficulty == "high": certifications.append("IEC 61215")
        title = f"Installation of Grid-Connected Rooftop Solar PV Systems ({seq_num} MW)"
        scope = "Design, supply, installation, testing, and commissioning of grid-connected rooftop solar PV systems. Includes 5 years of comprehensive maintenance contract (CMC). Must comply with MNRE technical specifications."
        
    elif code == "HEALTHCARE":
        issuer = random.choice(["NHM", "AIIMS", "State Health Department"])
        certifications = ["ISO 13485", "CDSCO Registration"]
        if difficulty == "high": certifications.append("NABH")
        title = f"Supply and Commissioning of Advanced Diagnostic Equipment Block {seq_num}"
        scope = "Procurement, installation, and commissioning of MRI and CT scan machines for district hospitals. Vendor must provide operational training to medical staff. Includes 3-year warranty and AMC."
        
    elif code == "WATER":
        issuer = random.choice(["AMRUT", "State Water Board", "JNNURM"])
        certifications = ["ISO 9001", "BIS"]
        title = f"Augmentation of Water Supply Scheme and STP Construction Zone {seq_num}"
        scope = "Laying of DI pipes for water supply distribution network. Construction of a 5 MLD Sewage Treatment Plant (STP) based on SBR technology. Includes SCADA implementation for monitoring."
        
    elif code == "ELECTRICAL":
        issuer = random.choice(["PGCIL", "State DISCOM", "Industrial Estate Authority"])
        certifications = ["CEA License", "ISO 9001"]
        if difficulty == "high": certifications.append("CPRI Test Certification")
        title = f"Establishment of 33/11kV Substation and HT/LT Cabling ({seq_num})"
        scope = "Turnkey contract for establishing a 33/11kV substation including transformers, breakers, and control panels. Laying of underground HT and LT cables in urban areas. Integration with existing grid."
        
    elif code == "ROADS":
        issuer = random.choice(["NHAI", "State PWD", "PMGSY"])
        certifications = ["NHAI Empanelment", "IRC Compliance", "ISO 9001"]
        title = f"Four-Laning of State Highway Section {seq_num}"
        scope = "Widening and strengthening of existing 2-lane road to 4-lane divided carriageway with paved shoulders. Construction of major and minor bridges along the alignment. Defect liability period of 5 years."
        
    elif code == "SUPPLY":
        issuer = random.choice(["DGS&D", "GeM", "State Secretariat"])
        certifications = ["GeM Registration", "BIS"]
        title = f"Rate Contract for Supply of Office Furniture and IT Peripherals {seq_num}"
        scope = "Annual rate contract for the supply of modular office furniture, ergonomic chairs, and standard IT peripherals. Delivery must be made to various government offices across the state within 14 days of PO issuance."
        
    elif code == "CONSULTANCY":
        issuer = random.choice(["NITI Aayog", "State Planning Board"])
        certifications = ["ICAI/ICSI/RICS Membership"]
        title = f"Project Management Consultancy for Smart City Mission {seq_num}"
        scope = "Provide comprehensive project management consultancy (PMC) services. Includes preparation of DPRs, tender document preparation, and on-site project monitoring. Team must deploy domain experts in urban planning and finance."
        
    elif code == "TELECOM":
        issuer = random.choice(["BSNL", "DoT", "State Police Department"])
        certifications = ["TEC Approval", "ISO 9001"]
        title = f"Deployment of Secure TETRA Communication Network Area {seq_num}"
        scope = "Supply, installation, and commissioning of a secure digital trunked radio (TETRA) network for emergency services. Includes base stations, mobile terminals, and centralized dispatch system. Must ensure 99.9% uptime."

    return {
        "tender_id": f"TM-EVAL-{code}-{seq_num:03d}",
        "title": title,
        "sector": domain,
        "issuing_authority": issuer,
        "location": random.choice(STATES),
        "district": "Capital District",
        "scope_of_work": scope,
        "min_turnover": min_turnover,
        "min_experience_years": min_exp,
        "estimated_value": est_value,
        "mandatory_certifications": certifications,
        "submission_deadline": (datetime.now() + timedelta(days=random.randint(15, 90))).strftime("%Y-%m-%d"),
        "duration_months": random.randint(3, 36),
        "eligibility_notes": f"This is a {difficulty} threshold tender requiring robust financial standing and specific domain experience.",
        "source_portal": random.choice(PORTALS),
        "_difficulty_level": difficulty # Internal tracking
    }

def generate_all_tenders():
    tenders = []
    seq = 1
    for domain_info in DOMAINS:
        for _ in range(domain_info["count"]):
            diff = difficulties.pop()
            tenders.append(generate_tender(domain_info, seq, diff))
            seq += 1
            
    out_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "data")
    os.makedirs(out_dir, exist_ok=True)
    out_path = os.path.join(out_dir, "tenders_50.json")
    
    with open(out_path, "w") as f:
        json.dump(tenders, f, indent=2)
        
    print(f"Generated {len(tenders)} tenders in {out_path}")
    print("\nSample of 3 tenders:")
    print(json.dumps(tenders[:3], indent=2))

if __name__ == "__main__":
    generate_all_tenders()
