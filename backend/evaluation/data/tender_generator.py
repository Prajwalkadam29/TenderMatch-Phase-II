import json
import os
import argparse
from datetime import datetime, timedelta, timezone
import random

def generate_tenders():
    SCRIPT_VERSION = "1.0.0"
    
    distribution = [
        {"domain": "Civil & Construction", "count": 9},
        {"domain": "IT & Software", "count": 8},
        {"domain": "Renewable Energy", "count": 7},
        {"domain": "Healthcare & Medical", "count": 6},
        {"domain": "Water & Sanitation", "count": 5},
        {"domain": "Electrical & Instrumentation", "count": 5},
        {"domain": "Roads & Highways", "count": 4},
        {"domain": "Supply & Procurement", "count": 3},
        {"domain": "Consultancy & Advisory", "count": 2},
        {"domain": "Telecom & Networking", "count": 1}
    ]
    
    difficulties = ["low"] * 15 + ["medium"] * 20 + ["high"] * 15
    random.shuffle(difficulties)
    
    # Base Data Mappings
    issuers = {
        "Civil & Construction": ["CPWD", "UP PWD", "Maharashtra PWD", "Pune Smart City SPV"],
        "IT & Software": ["NIC", "MeitY", "Gujarat Informatics Ltd", "SBI IT Division"],
        "Renewable Energy": ["SECI", "MNRE", "Tamil Nadu TANGEDCO", "Gujarat GUVNL"],
        "Healthcare & Medical": ["NHM", "AIIMS Delhi", "ESIC", "Kerala Health Dept"],
        "Water & Sanitation": ["AMRUT Mission", "Delhi Jal Board", "UP Jal Nigam"],
        "Electrical & Instrumentation": ["PGCIL", "BHEL", "Tata Power DDL"],
        "Roads & Highways": ["NHAI", "PMGSY", "MSRDC"],
        "Supply & Procurement": ["DGS&D", "GeM SPV", "FCI"],
        "Consultancy & Advisory": ["NITI Aayog", "Ministry of Finance", "Invest India"],
        "Telecom & Networking": ["BSNL", "DoT", "RailTel"]
    }
    
    cert_pools = {
        "Civil & Construction": ["ISO 9001:2015", "BIS license", "CPWD empanelment"],
        "IT & Software": ["ISO 27001", "CMMI Level 3", "CMMI Level 5", "GEM registration"],
        "Renewable Energy": ["MNRE empanelment", "BIS IS 14286", "IEC 61215"],
        "Healthcare & Medical": ["ISO 13485", "CDSCO registration", "NABH"],
        "Water & Sanitation": ["BIS", "ISO 9001", "WHO-GMP"],
        "Electrical & Instrumentation": ["CEA license", "ISO 9001", "CPRI test certification"],
        "Roads & Highways": ["NHAI empanelment", "IRC compliance", "ISO 9001"],
        "Supply & Procurement": ["GeM registration", "BIS", "ISO 9001"],
        "Consultancy & Advisory": ["ICAI membership", "ICSI membership", "ISO 9001"],
        "Telecom & Networking": ["TEC approval", "ISO 9001", "ISO 27001"]
    }
    
    project_topics = {
        "Civil & Construction": ["building construction", "sports complex civil work", "drainage network setup", "flyover extension", "metro civil works", "housing project"],
        "IT & Software": ["ERP implementation", "citizen mobile app", "data center upgrade", "cybersecurity audit", "cloud migration", "e-governance portal"],
        "Renewable Energy": ["rooftop solar installation", "ground-mounted solar park", "wind O&M services", "solar pump installation", "hybrid microgrid"],
        "Healthcare & Medical": ["medical equipment supply", "hospital management software", "ambulance fleet services", "diagnostic lab setup", "ICU ventilator supply"],
        "Water & Sanitation": ["water treatment plant", "sewage pipeline", "water supply scheme", "STP construction", "rural water ATM"],
        "Electrical & Instrumentation": ["132kV substation", "smart street lighting", "SCADA implementation", "HT/LT cabling", "transformer maintenance"],
        "Roads & Highways": ["4-lane highway expansion", "rural road construction", "bridge rehabilitation", "toll plaza maintenance", "expressway paving"],
        "Supply & Procurement": ["office furniture", "PPE supply", "stationery and printing", "industrial uniforms"],
        "Consultancy & Advisory": ["project management consultancy", "financial audit services", "environmental impact study"],
        "Telecom & Networking": ["optical fiber laying", "5G network equipment", "V-SAT connectivity"]
    }
    
    locations = [
        {"state": "Maharashtra", "district": "Pune"},
        {"state": "Gujarat", "district": "Ahmedabad"},
        {"state": "Delhi", "district": "New Delhi"},
        {"state": "Karnataka", "district": "Bengaluru"},
        {"state": "Uttar Pradesh", "district": "Lucknow"},
        {"state": "Tamil Nadu", "district": "Chennai"},
        {"state": "Kerala", "district": "Ernakulam"}
    ]
    
    portals = ["gem.gov.in", "cppp.nic.in", "etender.up.gov.in", "mahatenders.gov.in"]
    
    tenders = []
    
    seq = 1
    diff_idx = 0
    
    for dist in distribution:
        domain = dist["domain"]
        count = dist["count"]
        domain_code = domain.split()[0].upper().replace("&", "")
        
        for _ in range(count):
            diff = difficulties[diff_idx]
            diff_idx += 1
            
            # Difficulty mapping
            if diff == "low":
                turnover = random.randint(5_000_00, 20_000_000)  # 5L to 2Cr
                exp = random.randint(1, 3)
                num_certs = 1
            elif diff == "medium":
                turnover = random.randint(20_000_000, 150_000_000) # 2Cr to 15Cr
                exp = random.randint(4, 7)
                num_certs = 2
            else: # high
                turnover = random.randint(150_000_000, 1000_000_000) # 15Cr to 100Cr
                exp = random.randint(8, 15)
                num_certs = random.randint(2, 4)
                
            est_value = int(turnover * random.uniform(1.5, 3.0))
            
            topic = random.choice(project_topics[domain])
            loc = random.choice(locations)
            
            certs = random.sample(cert_pools[domain], min(num_certs, len(cert_pools[domain])))
            if diff == "high" and "GeM registration" not in certs:
                certs.append("GeM registration") # common requirement
                
            t_id = f"TM-EVAL-{domain_code}-{seq:03d}"
            
            scope = f"The selected vendor will be responsible for the complete execution of the {topic} project in {loc['district']}, {loc['state']}. "
            scope += f"This includes end-to-end implementation, quality assurance, and adherence to {domain} standards. "
            scope += "The vendor must ensure timely delivery and maintain strict compliance with all statutory regulations."
            
            days_out = random.randint(15, 90)
            deadline = (datetime.now(timezone.utc) + timedelta(days=days_out)).isoformat()
            
            tender = {
                "tender_id": t_id,
                "title": f"RFP for {topic.title()} in {loc['district']}",
                "sector": domain,
                "issuing_authority": random.choice(issuers[domain]),
                "location": loc["state"],
                "district": loc["district"],
                "scope_of_work": scope,
                "min_turnover": turnover,
                "min_experience_years": exp,
                "estimated_value": est_value,
                "mandatory_certifications": list(set(certs)),
                "submission_deadline": deadline,
                "duration_months": random.randint(3, 36),
                "eligibility_notes": f"Bidders must demonstrate strong capacity. Minimum turnover of INR {turnover} required.",
                "source_portal": random.choice(portals),
                "_difficulty": diff  # internal metadata tracking
            }
            
            tenders.append(tender)
            seq += 1
            
    return {
        "metadata": {
            "generated_at": datetime.now(timezone.utc).isoformat(),
            "script_version": SCRIPT_VERSION,
            "total_tenders": len(tenders)
        },
        "tenders": tenders
    }

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Generate 50 synthetic tenders for evaluation.")
    parser.add_argument("--force", action="store_true", help="Overwrite existing dataset")
    args = parser.parse_args()
    
    output_path = os.path.join(os.path.dirname(__file__), "tenders_50.json")
    
    if os.path.exists(output_path) and not args.force:
        print(f"Error: {output_path} already exists. Use --force to overwrite.")
        exit(1)
        
    data = generate_tenders()
    
    with open(output_path, "w") as f:
        json.dump(data, f, indent=4)
        
    print(f"Successfully generated {len(data['tenders'])} tenders at {output_path}")
    
    # Print sample of 3 tenders for verification
    print("\nSample Tenders:")
    print("===============")
    for i in range(3):
        print(json.dumps(data["tenders"][i], indent=2))
        print("---")
