#!/usr/bin/env python3
"""
Add additional student data: certificates and profile updates
"""

import asyncio
import sys
import uuid
from pathlib import Path

# Add the backend directory to Python path
backend_dir = Path(__file__).parent
sys.path.insert(0, str(backend_dir))

from sqlalchemy import select, update
from app.core.database import async_session_factory
from app.models.auth import AuthUser, Certificate


async def add_certificates(student_id):
    """Add sample certificates for the student"""
    
    certificates_data = [
        {
            "title": "Python Programming Certification",
            "description": "Completed advanced Python programming course with distinction",
            "file_name": "python_cert.pdf",
            "file_path": "certificates/python_cert.pdf",
            "points": 10
        },
        {
            "title": "Web Development Bootcamp",
            "description": "Full-stack web development with React and Node.js",
            "file_name": "web_dev_cert.pdf",
            "file_path": "certificates/web_dev_cert.pdf",
            "points": 15
        },
        {
            "title": "Machine Learning Workshop",
            "description": "Hands-on machine learning with TensorFlow",
            "file_name": "ml_workshop.pdf",
            "file_path": "certificates/ml_workshop.pdf",
            "points": 12
        },
        {
            "title": "Cloud Computing Fundamentals",
            "description": "AWS cloud architecture and deployment",
            "file_name": "cloud_cert.pdf",
            "file_path": "certificates/cloud_cert.pdf",
            "points": 8
        },
        {
            "title": "Data Science Competition",
            "description": "2nd place in inter-college data science competition",
            "file_name": "data_science_comp.pdf",
            "file_path": "certificates/data_science_comp.pdf",
            "points": 20
        }
    ]
    
    async with async_session_factory() as session:
        # Check if certificates already exist
        existing = await session.execute(
            select(Certificate).where(Certificate.student_id == student_id)
        )
        if existing.scalars().first():
            print("Certificates already exist. Clearing existing data...")
            await session.execute(
                select(Certificate).where(Certificate.student_id == student_id)
            )
            # Delete existing certificates
            for cert in existing.scalars().all():
                await session.delete(cert)
            await session.commit()
        
        # Add new certificates
        for cert_data in certificates_data:
            certificate = Certificate(
                student_id=student_id,
                title=cert_data["title"],
                description=cert_data["description"],
                file_name=cert_data["file_name"],
                file_path=cert_data["file_path"],
                is_verified=True,  # Mark as verified for demo
                points=cert_data["points"]
            )
            session.add(certificate)
        
        await session.commit()
        print(f"✅ Added {len(certificates_data)} certificates")


async def update_student_profile(student_id):
    """Update student profile with additional information"""
    
    async with async_session_factory() as session:
        # Update student profile
        await session.execute(
            update(AuthUser)
            .where(AuthUser.id == student_id)
            .values(
                department="Computer Science and Engineering",
                semester=4,
                roll_number="CS2021001",
                phone_number="+91-9876543210",
                goal="To become a full-stack software engineer and specialize in AI/ML technologies",
                skills=["Python", "JavaScript", "React", "Node.js", "Machine Learning", "AWS", "Docker", "MongoDB"],
                resume_url="https://example.com/resume/neel_resume.pdf"
            )
        )
        await session.commit()
        print("✅ Updated student profile with additional information")


async def show_summary(student_id):
    """Show a summary of the populated data"""
    
    async with async_session_factory() as session:
        # Get student info
        result = await session.execute(
            select(AuthUser).where(AuthUser.id == student_id)
        )
        student = result.scalar_one()
        
        # Get certificates
        result = await session.execute(
            select(Certificate).where(Certificate.student_id == student_id)
        )
        certificates = result.scalars().all()
        
        print("\n📋 Student Profile Summary:")
        print("=" * 50)
        print(f"Name: {student.name}")
        print(f"Email: {student.email}")
        print(f"Department: {student.department}")
        print(f"Semester: {student.semester}")
        print(f"Roll Number: {student.roll_number}")
        print(f"Phone: {student.phone_number}")
        print(f"Goal: {student.goal}")
        print(f"Skills: {', '.join(student.skills) if student.skills else 'None'}")
        print(f"Certificates: {len(certificates)}")
        print(f"Total Certificate Points: {sum(c.points for c in certificates)}")
        
        print("\n🏆 Certificates:")
        for cert in certificates:
            status = "✅ Verified" if cert.is_verified else "⏳ Pending"
            print(f"  • {cert.title} ({cert.points} points) - {status}")


async def main():
    """Main function"""
    print("🚀 Adding additional student data...")
    
    # Get student ID for goodcurser@gmail.com
    async with async_session_factory() as session:
        result = await session.execute(
            select(AuthUser).where(AuthUser.email == "goodcurser@gmail.com")
        )
        student = result.scalar_one_or_none()
        
        if not student:
            print("❌ Student not found!")
            return
        
        student_id = student.id
        print(f"Found student: {student.name}")
    
    # Add certificates
    await add_certificates(student_id)
    
    # Update profile
    await update_student_profile(student_id)
    
    # Show summary
    await show_summary(student_id)
    
    print("\n✅ Additional data population completed!")
    print("🎓 Student dashboard now has complete profile and certificates data.")


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except Exception as e:
        print(f"\n❌ Error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
