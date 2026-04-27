from typing import List
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from .. import models, schemas, security
from ..database import get_db

router = APIRouter(prefix="/patients", tags=["patients"])


@router.post("", response_model=schemas.PatientOut, status_code=201)
def create_patient(data: schemas.PatientCreate, db: Session = Depends(get_db),
                   current=Depends(security.get_current_user)):
    if db.query(models.Patient).filter(models.Patient.user_id == current["user_id"]).first():
        raise HTTPException(status_code=409, detail="Patient profile already exists")
    patient = models.Patient(user_id=current["user_id"], **data.model_dump())
    db.add(patient)
    db.commit()
    db.refresh(patient)
    return patient


@router.get("/me", response_model=schemas.PatientWithHistory)
def get_my_profile(db: Session = Depends(get_db), current=Depends(security.get_current_user)):
    patient = db.query(models.Patient).filter(models.Patient.user_id == current["user_id"]).first()
    if not patient:
        raise HTTPException(status_code=404, detail="Profile not found")
    return patient


@router.get("", response_model=List[schemas.PatientOut])
def list_patients(db: Session = Depends(get_db),
                  _=Depends(security.require_roles("practitioner", "secretary", "admin"))):
    return db.query(models.Patient).all()


@router.get("/{patient_id}", response_model=schemas.PatientWithHistory)
def get_patient(patient_id: UUID, db: Session = Depends(get_db),
                current=Depends(security.get_current_user)):
    patient = db.query(models.Patient).filter(models.Patient.id == patient_id).first()
    if not patient:
        raise HTTPException(status_code=404, detail="Patient not found")
    # Patients can only see their own; medical staff can see all
    if current["role"] == "patient" and str(patient.user_id) != current["user_id"]:
        raise HTTPException(status_code=403, detail="Forbidden")
    return patient


@router.put("/{patient_id}", response_model=schemas.PatientOut)
def update_patient(patient_id: UUID, data: schemas.PatientUpdate,
                   db: Session = Depends(get_db), current=Depends(security.get_current_user)):
    patient = db.query(models.Patient).filter(models.Patient.id == patient_id).first()
    if not patient:
        raise HTTPException(status_code=404, detail="Patient not found")
    if current["role"] == "patient" and str(patient.user_id) != current["user_id"]:
        raise HTTPException(status_code=403, detail="Forbidden")
    for field, value in data.model_dump(exclude_unset=True).items():
        setattr(patient, field, value)
    db.commit()
    db.refresh(patient)
    return patient


@router.post("/{patient_id}/history", response_model=schemas.HistoryOut, status_code=201)
def add_history(patient_id: UUID, data: schemas.HistoryCreate, db: Session = Depends(get_db),
                _=Depends(security.require_roles("practitioner", "secretary", "admin"))):
    patient = db.query(models.Patient).filter(models.Patient.id == patient_id).first()
    if not patient:
        raise HTTPException(status_code=404, detail="Patient not found")
    item = models.MedicalHistory(patient_id=patient_id, **data.model_dump())
    db.add(item)
    db.commit()
    db.refresh(item)
    return item


@router.get("/by-user/{user_id}", response_model=schemas.PatientOut)
def get_by_user(user_id: UUID, db: Session = Depends(get_db),
                _=Depends(security.get_current_user)):
    """Used by other services to resolve user_id → patient_id."""
    patient = db.query(models.Patient).filter(models.Patient.user_id == user_id).first()
    if not patient:
        raise HTTPException(status_code=404, detail="Patient not found")
    return patient
