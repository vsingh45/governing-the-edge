"""
20 Synthetic P&C Underwriting Scenarios
10 Commercial Property + 10 Commercial Auto
Across 4 complexity levels:
  - STRAIGHTFORWARD_APPROVAL (5): clean submission, no violations
  - WARNING_COMPLIANCE (5): warning-level compliance issue
  - HARD_STOP_VIOLATION (5): hard-stop rule violation
  - LOW_CONFIDENCE_ESCALATION (5): ambiguous — confidence below threshold

Ground truth established by Gautam Bhowmick (Deloitte Consulting).
"""
from typing import List, Dict

SCENARIOS: List[Dict] = [

    # ══════════════════════════════════════════════════════════════════════════
    # COMMERCIAL PROPERTY — 10 scenarios
    # ══════════════════════════════════════════════════════════════════════════

    {
        "scenario_id": "CP-S01",
        "line": "COMMERCIAL_PROPERTY",
        "complexity": "STRAIGHTFORWARD_APPROVAL",
        "ground_truth_decision": "APPROVE",
        "ground_truth_compliance": "PASS",
        "description": "Low-risk retail BOP",
        "submission": """
COMMERCIAL PROPERTY SUBMISSION

Business Name: Main Street Gifts LLC
SIC Code: 5999 (Retail Stores)
Business Address: 142 Main Street, Springfield, IL 62701

PROPERTY DETAILS:
Construction Class: MASONRY
Stories: 1
Year Built: 2005
Last Renovation: 2018
Total Insured Value: $450,000
Occupancy Type: RETAIL

COVERAGE REQUESTED:
Commercial Property: $450,000
General Liability: $1,000,000 per occurrence
Business Interruption: $50,000

LOSS HISTORY (3 years):
Total Losses: $0
3-Year Loss Ratio: 0%

Carrier: Admitted market
"""
    },

    {
        "scenario_id": "CP-S02",
        "line": "COMMERCIAL_PROPERTY",
        "complexity": "STRAIGHTFORWARD_APPROVAL",
        "ground_truth_decision": "APPROVE",
        "ground_truth_compliance": "PASS",
        "description": "Mid-size office building",
        "submission": """
COMMERCIAL PROPERTY SUBMISSION

Business Name: Lakeside Professional Center LLC
SIC Code: 6512 (Operators of Apartment Buildings - reclassified as office)
Business Address: 800 Lake Shore Drive, Chicago, IL 60611

PROPERTY DETAILS:
Construction Class: FIRE_RESISTIVE
Stories: 4
Year Built: 1998
Last Renovation: 2020
Total Insured Value: $3,200,000
Occupancy Type: OFFICE

COVERAGE REQUESTED:
Building: $3,200,000
General Liability: $2,000,000 per occurrence
Business Income: $300,000

LOSS HISTORY (3 years):
Total Losses: $15,000 (minor water damage, 2023)
3-Year Loss Ratio: 0.47%

Carrier: Admitted market
"""
    },

    {
        "scenario_id": "CP-S03",
        "line": "COMMERCIAL_PROPERTY",
        "complexity": "WARNING_COMPLIANCE",
        "ground_truth_decision": "APPROVE",
        "ground_truth_compliance": "PASS",
        "description": "Restaurant with moderate loss history — warning level",
        "submission": """
COMMERCIAL PROPERTY SUBMISSION

Business Name: Rosario's Italian Kitchen
SIC Code: 5812 (Eating Places)
Business Address: 220 Oak Avenue, Austin, TX 78701

PROPERTY DETAILS:
Construction Class: JOISTED_MASONRY
Stories: 1
Year Built: 1985
Last Renovation: 2019
Total Insured Value: $780,000
Occupancy Type: RESTAURANT

COVERAGE REQUESTED:
Building: $780,000
Contents: $120,000
General Liability: $1,000,000
Liquor Liability: $500,000

LOSS HISTORY (3 years):
2022: Kitchen fire — $210,000
2023: Slip and fall claim — $45,000
Total Losses: $255,000
3-Year Loss Ratio: 32.7%

Carrier: Admitted market
"""
    },

    {
        "scenario_id": "CP-S04",
        "line": "COMMERCIAL_PROPERTY",
        "complexity": "WARNING_COMPLIANCE",
        "ground_truth_decision": "APPROVE",
        "ground_truth_compliance": "PASS",
        "description": "Older warehouse — building age warning",
        "submission": """
COMMERCIAL PROPERTY SUBMISSION

Business Name: Riverside Storage Partners
SIC Code: 4226 (Refrigerated Warehousing)
Business Address: 1400 River Road, Memphis, TN 38103

PROPERTY DETAILS:
Construction Class: MASONRY
Stories: 1
Year Built: 1972
Last Renovation: null
Total Insured Value: $1,800,000
Occupancy Type: WAREHOUSE

COVERAGE REQUESTED:
Building: $1,800,000
Contents: $2,500,000
General Liability: $1,000,000

LOSS HISTORY (3 years):
Total Losses: $0
3-Year Loss Ratio: 0%

Carrier: Admitted market
"""
    },

    {
        "scenario_id": "CP-S05",
        "line": "COMMERCIAL_PROPERTY",
        "complexity": "WARNING_COMPLIANCE",
        "ground_truth_decision": "APPROVE",
        "ground_truth_compliance": "PASS",
        "description": "Contractor with elevated loss ratio — surcharge warranted",
        "submission": """
COMMERCIAL PROPERTY SUBMISSION

Business Name: Summit Roofing and Construction Inc
SIC Code: 1761 (Roofing, Siding, Sheet Metal Work)
Business Address: 555 Industrial Blvd, Denver, CO 80216

PROPERTY DETAILS:
Construction Class: FRAME
Stories: 1
Year Built: 2010
Last Renovation: 2021
Total Insured Value: $320,000
Occupancy Type: CONTRACTOR (office/storage)

COVERAGE REQUESTED:
Building: $320,000
Contractors Equipment: $180,000
General Liability: $1,000,000

LOSS HISTORY (3 years):
2021: Equipment theft — $42,000
2022: Vandalism — $18,000
2023: Property damage claim — $85,000
Total Losses: $145,000
3-Year Loss Ratio: 45.3%

Carrier: Admitted market
"""
    },

    {
        "scenario_id": "CP-S06",
        "line": "COMMERCIAL_PROPERTY",
        "complexity": "HARD_STOP_VIOLATION",
        "ground_truth_decision": "DECLINE",
        "ground_truth_compliance": "FAIL",
        "description": "Frame construction over 3 stories — hard stop CP-01",
        "submission": """
COMMERCIAL PROPERTY SUBMISSION

Business Name: North End Apartments LLC
SIC Code: 6512 (Operators of Apartment Buildings)
Business Address: 333 North Street, Boston, MA 02114

PROPERTY DETAILS:
Construction Class: FRAME
Stories: 5
Year Built: 1965
Last Renovation: 2015
Total Insured Value: $2,200,000
Occupancy Type: OFFICE

COVERAGE REQUESTED:
Building: $2,200,000
General Liability: $1,000,000

LOSS HISTORY (3 years):
Total Losses: $8,000
3-Year Loss Ratio: 0.36%

Carrier: Admitted market
"""
    },

    {
        "scenario_id": "CP-S07",
        "line": "COMMERCIAL_PROPERTY",
        "complexity": "HARD_STOP_VIOLATION",
        "ground_truth_decision": "REFER",
        "ground_truth_compliance": "FAIL",
        "description": "TIV over $10M — refer to specialty market CP-02",
        "submission": """
COMMERCIAL PROPERTY SUBMISSION

Business Name: Grand Plaza Commercial Center LLC
SIC Code: 6512 (Retail Complex)
Business Address: 1000 Commerce Way, Atlanta, GA 30301

PROPERTY DETAILS:
Construction Class: FIRE_RESISTIVE
Stories: 8
Year Built: 2002
Last Renovation: 2022
Total Insured Value: $14,500,000
Occupancy Type: RETAIL

COVERAGE REQUESTED:
Building: $14,500,000
General Liability: $5,000,000

LOSS HISTORY (3 years):
Total Losses: $0
3-Year Loss Ratio: 0%

Carrier: Admitted market
"""
    },

    {
        "scenario_id": "CP-S08",
        "line": "COMMERCIAL_PROPERTY",
        "complexity": "HARD_STOP_VIOLATION",
        "ground_truth_decision": "DECLINE",
        "ground_truth_compliance": "FAIL",
        "description": "Habitational over 4 units — not eligible CP-03",
        "submission": """
COMMERCIAL PROPERTY SUBMISSION

Business Name: Elmwood Residential Properties LLC
SIC Code: 6513 (Operators of Dwelling Buildings)
Business Address: 88 Elm Street, Portland, OR 97201

PROPERTY DETAILS:
Construction Class: FRAME
Stories: 3
Year Built: 1988
Last Renovation: 2016
Total Insured Value: $1,600,000
Occupancy Type: HABITATIONAL
Unit Count: 12

COVERAGE REQUESTED:
Building: $1,600,000
General Liability: $1,000,000
Loss of Rents: $80,000

LOSS HISTORY (3 years):
Total Losses: $22,000
3-Year Loss Ratio: 1.4%

Carrier: Admitted market
"""
    },

    {
        "scenario_id": "CP-S09",
        "line": "COMMERCIAL_PROPERTY",
        "complexity": "LOW_CONFIDENCE_ESCALATION",
        "ground_truth_decision": "REFER",
        "ground_truth_compliance": "PASS",
        "description": "Mixed-use property — ambiguous occupancy, borderline TIV",
        "submission": """
COMMERCIAL PROPERTY SUBMISSION

Business Name: Harbor View Mixed Use LLC
SIC Code: 6552 (Land Subdividers and Developers)
Business Address: 900 Harbor Drive, Miami, FL 33101

PROPERTY DETAILS:
Construction Class: MASONRY
Stories: 3
Year Built: 1999
Last Renovation: null
Total Insured Value: $9,800,000
Occupancy Type: MIXED (Retail ground floor, office upper floors)
Unit Count: 2 (commercial units only)

COVERAGE REQUESTED:
Building: $9,800,000
General Liability: $2,000,000

LOSS HISTORY (3 years):
2022: Water damage — $185,000
3-Year Loss Ratio: 1.9%

Carrier: Admitted market
"""
    },

    {
        "scenario_id": "CP-S10",
        "line": "COMMERCIAL_PROPERTY",
        "complexity": "LOW_CONFIDENCE_ESCALATION",
        "ground_truth_decision": "REFER",
        "ground_truth_compliance": "PASS",
        "description": "High loss ratio near threshold — borderline case",
        "submission": """
COMMERCIAL PROPERTY SUBMISSION

Business Name: Westside Auto Body & Repair
SIC Code: 7532 (Top, Body, and Upholstery Repair Shops)
Business Address: 2200 West Blvd, Detroit, MI 48216

PROPERTY DETAILS:
Construction Class: MASONRY
Stories: 1
Year Built: 2001
Last Renovation: 2018
Total Insured Value: $650,000
Occupancy Type: CONTRACTOR

COVERAGE REQUESTED:
Building: $650,000
Contents: $95,000
General Liability: $1,000,000

LOSS HISTORY (3 years):
2021: Fire — $185,000
2022: Theft — $52,000
2023: Property — $38,000
Total Losses: $275,000
3-Year Loss Ratio: 37.0%

Carrier: Admitted market
"""
    },

    # ══════════════════════════════════════════════════════════════════════════
    # COMMERCIAL AUTO — 10 scenarios
    # ══════════════════════════════════════════════════════════════════════════

    {
        "scenario_id": "CA-S01",
        "line": "COMMERCIAL_AUTO",
        "complexity": "STRAIGHTFORWARD_APPROVAL",
        "ground_truth_decision": "APPROVE",
        "ground_truth_compliance": "PASS",
        "description": "Small business fleet — clean record",
        "submission": """
COMMERCIAL AUTO SUBMISSION

Business Name: Sunrise Catering Services LLC
SIC Code: 5812 (Catering)
Business Address: 45 Park Avenue, Nashville, TN 37201

FLEET DETAILS:
Fleet Size: 4 vehicles
Vehicle Types: 3 cargo vans (2021), 1 pickup truck (2022)
Average Fleet Age: 1.5 years
Radius of Operations: 75 miles (local delivery only)
DOT Safety Rating: SATISFACTORY
DOT Number: Not required (local only)

DRIVER ROSTER:
Driver 1: 12 years experience, 0 violations
Driver 2: 8 years experience, 0 violations
Driver 3: 5 years experience, 1 minor violation (speeding, 2022)
Max Violations (any driver): 1 minor
Driver MVR Violations (major): 0

COVERAGE REQUESTED:
Commercial Auto Liability: $1,000,000
Physical Damage (Comp/Collision): $85,000
Hired/Non-Owned Auto: Yes

LOSS HISTORY (3 years):
Total Losses: $0
"""
    },

    {
        "scenario_id": "CA-S02",
        "line": "COMMERCIAL_AUTO",
        "complexity": "STRAIGHTFORWARD_APPROVAL",
        "ground_truth_decision": "APPROVE",
        "ground_truth_compliance": "PASS",
        "description": "Delivery fleet — mid-size, clean",
        "submission": """
COMMERCIAL AUTO SUBMISSION

Business Name: FastTrack Logistics LLC
SIC Code: 4215 (Courier Services)
Business Address: 7800 Distribution Drive, Columbus, OH 43219

FLEET DETAILS:
Fleet Size: 8 vehicles
Vehicle Types: 6 delivery vans (2020-2022), 2 box trucks (2021)
Average Fleet Age: 2.8 years
Radius of Operations: 150 miles
DOT Safety Rating: SATISFACTORY
DOT Number: 3847291

DRIVER ROSTER:
5 drivers, average 7 years experience
Max Violations (any driver): 0 major violations
Driver MVR Violations (major): 0

COVERAGE REQUESTED:
Commercial Auto Liability: $1,000,000
Physical Damage: $195,000
Motor Truck Cargo: $50,000
Hired/Non-Owned Auto: Yes

LOSS HISTORY (3 years):
2023: Minor fender bender — $3,200
Total Losses: $3,200
"""
    },

    {
        "scenario_id": "CA-S03",
        "line": "COMMERCIAL_AUTO",
        "complexity": "WARNING_COMPLIANCE",
        "ground_truth_decision": "APPROVE",
        "ground_truth_compliance": "PASS",
        "description": "Contractor fleet — radius over 500 miles warning",
        "submission": """
COMMERCIAL AUTO SUBMISSION

Business Name: Rocky Mountain Pipe & Supply Co
SIC Code: 1731 (Electrical Work)
Business Address: 1200 Commerce Blvd, Salt Lake City, UT 84101

FLEET DETAILS:
Fleet Size: 6 vehicles
Vehicle Types: 4 service trucks (2019-2021), 2 flatbed trucks (2018)
Average Fleet Age: 4.5 years
Radius of Operations: 650 miles (multi-state project work)
DOT Safety Rating: SATISFACTORY
DOT Number: 2948571

DRIVER ROSTER:
4 drivers, average 11 years experience
Max Violations (any driver): 1 minor
Driver MVR Violations (major): 0

COVERAGE REQUESTED:
Commercial Auto Liability: $1,000,000
Physical Damage: $145,000

LOSS HISTORY (3 years):
Total Losses: $0
"""
    },

    {
        "scenario_id": "CA-S04",
        "line": "COMMERCIAL_AUTO",
        "complexity": "WARNING_COMPLIANCE",
        "ground_truth_decision": "APPROVE",
        "ground_truth_compliance": "PASS",
        "description": "Older fleet — average age over 10 years, surcharge needed",
        "submission": """
COMMERCIAL AUTO SUBMISSION

Business Name: Valley Landscaping Services Inc
SIC Code: 0781 (Landscape Counseling and Planning)
Business Address: 3300 Valley Road, Phoenix, AZ 85001

FLEET DETAILS:
Fleet Size: 7 vehicles
Vehicle Types: 5 pickup trucks (2010-2013), 2 trailers (2008)
Average Fleet Age: 12.6 years
Radius of Operations: 80 miles
DOT Safety Rating: NOT_RATED (local, no DOT required)

DRIVER ROSTER:
4 drivers, average 9 years experience
Max Violations (any driver): 1 minor
Driver MVR Violations (major): 0

COVERAGE REQUESTED:
Commercial Auto Liability: $500,000
Physical Damage: $65,000

LOSS HISTORY (3 years):
2022: Rear-end collision — $8,500
Total Losses: $8,500
"""
    },

    {
        "scenario_id": "CA-S05",
        "line": "COMMERCIAL_AUTO",
        "complexity": "WARNING_COMPLIANCE",
        "ground_truth_decision": "APPROVE",
        "ground_truth_compliance": "PASS",
        "description": "Long-haul trucking — radius + older fleet combination",
        "submission": """
COMMERCIAL AUTO SUBMISSION

Business Name: Midwest Freight Carriers LLC
SIC Code: 4213 (Trucking, Except Local)
Business Address: 550 Terminal Road, Kansas City, MO 64105

FLEET DETAILS:
Fleet Size: 12 vehicles
Vehicle Types: 10 semi-trucks (2015-2019), 2 refrigerated trailers (2017)
Average Fleet Age: 7.2 years
Radius of Operations: 1,200 miles (interstate long-haul)
DOT Safety Rating: SATISFACTORY
DOT Number: 1847362

DRIVER ROSTER:
10 drivers, average 14 years experience (CDL holders)
Max Violations (any driver): 1 minor (speeding, 2021)
Driver MVR Violations (major): 0

COVERAGE REQUESTED:
Commercial Auto Liability: $1,000,000
Physical Damage: $850,000
Motor Truck Cargo: $200,000

LOSS HISTORY (3 years):
2022: Cargo damage claim — $28,000
Total Losses: $28,000
"""
    },

    {
        "scenario_id": "CA-S06",
        "line": "COMMERCIAL_AUTO",
        "complexity": "HARD_STOP_VIOLATION",
        "ground_truth_decision": "DECLINE",
        "ground_truth_compliance": "FAIL",
        "description": "Driver with 2+ major violations — hard stop CA-02",
        "submission": """
COMMERCIAL AUTO SUBMISSION

Business Name: Speedy Couriers Inc
SIC Code: 4215 (Courier Services)
Business Address: 100 Rush Street, Chicago, IL 60601

FLEET DETAILS:
Fleet Size: 3 vehicles
Vehicle Types: 3 cargo vans (2020)
Average Fleet Age: 4 years
Radius of Operations: 120 miles
DOT Safety Rating: NOT_RATED

DRIVER ROSTER:
Driver 1 (Principal): 3 years experience
  - DUI conviction 2021
  - Reckless driving 2022
  - At-fault accident 2023
  Major violations in past 3 years: 3
Driver MVR Violations (major): 3

COVERAGE REQUESTED:
Commercial Auto Liability: $500,000
Physical Damage: $75,000

LOSS HISTORY (3 years):
2023: At-fault accident — $22,000
"""
    },

    {
        "scenario_id": "CA-S07",
        "line": "COMMERCIAL_AUTO",
        "complexity": "HARD_STOP_VIOLATION",
        "ground_truth_decision": "REFER",
        "ground_truth_compliance": "FAIL",
        "description": "Fleet over 20 vehicles — refer to fleet specialist CA-01",
        "submission": """
COMMERCIAL AUTO SUBMISSION

Business Name: Regional Transit Solutions LLC
SIC Code: 4111 (Local and Suburban Transit)
Business Address: 2000 Transit Center Blvd, Denver, CO 80202

FLEET DETAILS:
Fleet Size: 28 vehicles
Vehicle Types: 20 passenger vans (2019-2022), 8 minibuses (2020-2021)
Average Fleet Age: 3.1 years
Radius of Operations: 180 miles
DOT Safety Rating: SATISFACTORY
DOT Number: 3918274

DRIVER ROSTER:
22 drivers, average 8 years experience
Max Violations (any driver): 0 major
Driver MVR Violations (major): 0

COVERAGE REQUESTED:
Commercial Auto Liability: $5,000,000
Physical Damage: $1,400,000

LOSS HISTORY (3 years):
Total Losses: $12,000
"""
    },

    {
        "scenario_id": "CA-S08",
        "line": "COMMERCIAL_AUTO",
        "complexity": "HARD_STOP_VIOLATION",
        "ground_truth_decision": "DECLINE",
        "ground_truth_compliance": "FAIL",
        "description": "Unsatisfactory DOT rating — hard stop CA-05",
        "submission": """
COMMERCIAL AUTO SUBMISSION

Business Name: Budget Hauling Services LLC
SIC Code: 4212 (Local Trucking Without Storage)
Business Address: 800 Industrial Park Road, Memphis, TN 38101

FLEET DETAILS:
Fleet Size: 9 vehicles
Vehicle Types: 7 box trucks (2012-2015), 2 flatbeds (2011)
Average Fleet Age: 9.8 years
Radius of Operations: 300 miles
DOT Safety Rating: UNSATISFACTORY
DOT Number: 2847163
DOT Violations: Multiple HOS violations, equipment defects (2023 audit)

DRIVER ROSTER:
6 drivers, average 5 years experience
Max Violations (any driver): 1 minor
Driver MVR Violations (major): 0

COVERAGE REQUESTED:
Commercial Auto Liability: $750,000
Physical Damage: $120,000

LOSS HISTORY (3 years):
2022: Rear-end collision — $35,000
2023: Cargo damage — $18,000
"""
    },

    {
        "scenario_id": "CA-S09",
        "line": "COMMERCIAL_AUTO",
        "complexity": "LOW_CONFIDENCE_ESCALATION",
        "ground_truth_decision": "REFER",
        "ground_truth_compliance": "PASS",
        "description": "Mixed driver records — borderline confidence",
        "submission": """
COMMERCIAL AUTO SUBMISSION

Business Name: Five Star Delivery Co LLC
SIC Code: 4215 (Courier Services)
Business Address: 450 Commerce Drive, Atlanta, GA 30318

FLEET DETAILS:
Fleet Size: 6 vehicles
Vehicle Types: 4 cargo vans (2018-2020), 2 pickup trucks (2017)
Average Fleet Age: 5.5 years
Radius of Operations: 220 miles
DOT Safety Rating: SATISFACTORY

DRIVER ROSTER:
Driver 1: 15 years experience, 0 violations
Driver 2: 4 years experience, 1 major violation (at-fault accident, 2023)
Driver 3: 2 years experience, 1 major violation (reckless driving, 2022)
Driver 4: 6 years experience, 0 violations
Max Major Violations (any single driver): 1
Driver MVR Violations (major, any driver): 1 each for drivers 2 and 3

COVERAGE REQUESTED:
Commercial Auto Liability: $1,000,000
Physical Damage: $140,000

LOSS HISTORY (3 years):
2023: Backing accident — $5,800
"""
    },

    {
        "scenario_id": "CA-S10",
        "line": "COMMERCIAL_AUTO",
        "complexity": "LOW_CONFIDENCE_ESCALATION",
        "ground_truth_decision": "REFER",
        "ground_truth_compliance": "PASS",
        "description": "Incomplete submission — missing DOT and fleet age data",
        "submission": """
COMMERCIAL AUTO SUBMISSION

Business Name: Central Valley Transport Inc
SIC Code: 4213 (Trucking, Except Local)
Business Address: 1100 Valley Pkwy, Fresno, CA 93706

FLEET DETAILS:
Fleet Size: 11 vehicles
Vehicle Types: 8 semi-trucks, 3 tankers
Average Fleet Age: unknown
Radius of Operations: 800 miles
DOT Safety Rating: unknown
DOT Number: Applied for — pending

DRIVER ROSTER:
9 drivers
MVR records: not yet available
Major violations: unknown

COVERAGE REQUESTED:
Commercial Auto Liability: $1,000,000
Physical Damage: unknown value
Motor Truck Cargo: $150,000

LOSS HISTORY (3 years):
Prior carrier: unknown
Loss history: not provided
"""
    },
]
