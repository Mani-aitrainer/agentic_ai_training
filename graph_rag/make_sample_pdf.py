"""
Generates a sample, domain-neutral PDF describing a small company's
people, departments, and reporting/collaboration relationships.
This is the input document our pipeline will extract a graph from.
"""
from reportlab.lib.pagesizes import letter
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer
from reportlab.lib.styles import getSampleStyleSheet

doc = SimpleDocTemplate("company_overview.pdf", pagesize=letter)
styles = getSampleStyleSheet()
story = []

story.append(Paragraph("Northwind Robotics — Company Overview", styles["Title"]))
story.append(Spacer(1, 12))

body_text = """
Northwind Robotics is a mid-sized robotics company organized into three
departments: Engineering, Sales, and Operations.

Priya Sharma is the Chief Executive Officer of Northwind Robotics. She
directly oversees Arjun Mehta, who leads the Engineering department as
VP of Engineering, and Lisa Chen, who leads the Sales department as VP
of Sales.

Arjun Mehta manages two engineers: Ravi Kumar, a Senior Software
Engineer, and Meera Iyer, a Robotics Hardware Engineer. Ravi Kumar and
Meera Iyer collaborate closely on the AtlasBot product line.

Lisa Chen manages David Wong, an Account Executive, and Fatima Noor, a
Sales Operations Analyst. David Wong regularly coordinates with Ravi
Kumar on product demos for enterprise clients.

Operations is led by Carlos Rivera, Director of Operations, who
reports directly to Priya Sharma. Carlos Rivera manages Sana Aziz, the
Logistics Coordinator. Sana Aziz works with Meera Iyer to schedule
hardware shipments for pilot deployments.

Fatima Noor partners with Carlos Rivera on quarterly demand forecasting.
Meera Iyer also mentors an intern, Tom Becker, who is part of the
Engineering department.
"""

for para in body_text.strip().split("\n\n"):
    story.append(Paragraph(para.strip().replace("\n", " "), styles["Normal"]))
    story.append(Spacer(1, 10))

doc.build(story)
print("Created company_overview.pdf")
