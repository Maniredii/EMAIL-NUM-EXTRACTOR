"""
Utility script to generate sample resume PDFs for testing and demonstration.
Generates normal PDFs, multi-page PDFs, multiple emails, duplicates, corrupted, and zero-email PDFs.
"""
import os
import random
import fitz

FIRST_NAMES = [
    "James", "Mary", "John", "Patricia", "Robert", "Jennifer", "Michael", "Linda",
    "William", "Elizabeth", "David", "Barbara", "Richard", "Susan", "Joseph", "Jessica",
    "Thomas", "Sarah", "Charles", "Karen", "Christopher", "Nancy", "Daniel", "Lisa",
    "Matthew", "Betty", "Anthony", "Margaret", "Mark", "Sandra", "Donald", "Ashley"
]

LAST_NAMES = [
    "Smith", "Johnson", "Williams", "Brown", "Jones", "Garcia", "Miller", "Davis",
    "Rodriguez", "Martinez", "Hernandez", "Lopez", "Gonzalez", "Wilson", "Anderson",
    "Thomas", "Taylor", "Moore", "Jackson", "Martin", "Lee", "Perez", "Thompson", "White"
]

DOMAINS = ["gmail.com", "outlook.com", "yahoo.com", "techcorp.io", "consulting.com", "cloudcorp.net", "innovate.org"]

ROLES = [
    "Senior Python Developer", "Full Stack Engineer", "DevOps Specialist",
    "Data Scientist", "Product Manager", "Machine Learning Engineer",
    "Cloud Architect", "Frontend Developer", "QA Automation Engineer"
]


def generate_sample_batch(output_dir: str = "Sample_Resumes", count: int = 105):
    """Generates a folder of sample resume PDFs."""
    os.makedirs(output_dir, exist_ok=True)
    subfolders = ["Batch_Engineering", "Batch_DataScience", "Batch_Operations", "Sub_Nested/Batch_Archived"]
    for sub in subfolders:
        os.makedirs(os.path.join(output_dir, sub), exist_ok=True)

    shared_duplicate_email = "alex.shared.lead@globalrecruit.com"
    all_created = []

    print(f"Generating {count} sample resume PDFs in '{output_dir}'...")

    for i in range(1, count + 1):
        # Determine target folder (root or subfolder)
        if i % 3 == 0:
            target_folder = os.path.join(output_dir, subfolders[(i // 3) % len(subfolders)])
        else:
            target_folder = output_dir

        fname = random.choice(FIRST_NAMES)
        lname = random.choice(LAST_NAMES)
        role = random.choice(ROLES)
        domain = random.choice(DOMAINS)

        filename = f"Resume_{i:03d}_{fname}_{lname}.pdf"
        file_path = os.path.join(target_folder, filename)

        # Case 1: Corrupted file (simulate 2 corrupted files in batch)
        if i in (15, 62):
            with open(file_path, "wb") as f:
                f.write(b"CORRUPTED_FILE_DATA_NOT_A_VALID_PDF_STREAM_FOR_TESTING")
            all_created.append(file_path)
            continue

        # Case 2: Resume with zero emails (simulate 5 files without emails)
        if i in (10, 30, 50, 70, 90):
            doc = fitz.open()
            page = doc.new_page()
            page.insert_text((50, 72), f"{fname} {lname}\nRole: {role}\nAddress: San Francisco, CA\nPhone: (555) 010-{i:04d}\nPortfolio: https://github.com/{fname.lower()}{lname.lower()}")
            page.insert_text((50, 180), "Professional Summary:\nExperienced professional with a track record of driving results and leading teams.")
            doc.save(file_path)
            doc.close()
            all_created.append(file_path)
            continue

        # Case 3: Resume with shared duplicate email
        if i in (5, 25, 45):
            primary_email = shared_duplicate_email
        else:
            primary_email = f"{fname.lower()}.{lname.lower()}{i}@{domain}"

        doc = fitz.open()
        p1 = doc.new_page()
        p1.insert_text((50, 72), f"{fname} {lname}\nRole: {role}\nPrimary Contact: {primary_email}\nPhone: (555) {i:03d}-9876")
        p1.insert_text((50, 180), "Experience:\n- Led distributed engineering teams.\n- Built scalable microservices and data pipelines.\n- Optimized operational bottlenecks by 40%.")

        # Case 4: Multi-page resume with second email on page 2 (every 7th file)
        if i % 7 == 0:
            secondary_email = f"{fname.lower()}.personal@{random.choice(DOMAINS)}"
            p2 = doc.new_page()
            p2.insert_text((50, 72), f"Additional Information:\nSecondary Email: {secondary_email}\nReferences available upon request.")

        # Case 5: Mailto link annotation (every 11th file)
        if i % 11 == 0:
            target_page = doc[0]
            mailto_email = f"{fname.lower()}.inquiries@{domain}"
            rect = fitz.Rect(50, 300, 250, 320)
            target_page.insert_text((50, 315), f"Direct Inquiries: {mailto_email}")
            target_page.insert_link({"kind": fitz.LINK_URI, "from": rect, "uri": f"mailto:{mailto_email}"})

        doc.save(file_path)
        doc.close()
        all_created.append(file_path)

    print(f"Successfully generated {len(all_created)} test resumes in '{output_dir}'.")
    return all_created


if __name__ == "__main__":
    generate_sample_batch()
