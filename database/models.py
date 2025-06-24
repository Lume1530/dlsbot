from sqlalchemy import Column, Integer, String, BigInteger, DateTime, Boolean, Text, Float
from sqlalchemy.ext.declarative import declarative_base
from datetime import datetime

Base = declarative_base()

class User(Base):
    __tablename__ = "users"
    
    user_id = Column(BigInteger, primary_key=True)
    username = Column(String(255), nullable=True)
    registered = Column(Integer, default=0)
    approved = Column(Boolean, default=False)
    total_views = Column(BigInteger, default=0)
    total_reels = Column(Integer, default=0)
    max_slots = Column(Integer, default=50)
    used_slots = Column(Integer, default=0)
    last_submission = Column(DateTime, nullable=True)
    created_at = Column(DateTime, default=datetime.now)

class Reel(Base):
    __tablename__ = "reels"
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(BigInteger, nullable=False)
    shortcode = Column(String(255), nullable=False, unique=True)
    url = Column(Text, nullable=True)
    username = Column(String(255), nullable=True)
    views = Column(BigInteger, default=0)
    likes = Column(BigInteger, default=0)
    comments = Column(BigInteger, default=0)
    caption = Column(Text, nullable=True)
    media_url = Column(Text, nullable=True)
    submitted_at = Column(DateTime, default=datetime.now)
    last_updated = Column(DateTime, default=datetime.now)
    created_at = Column(DateTime, default=datetime.now)

class AllowedAccount(Base):
    __tablename__ = "allowed_accounts"
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(BigInteger, nullable=False)
    insta_handle = Column(String(255), nullable=False)

class PaymentDetail(Base):
    __tablename__ = "payment_details"
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(BigInteger, nullable=False)
    usdt_address = Column(String(255), nullable=True)
    paypal_email = Column(String(255), nullable=True)
    upi_address = Column(String(255), nullable=True)
    created_at = Column(DateTime, default=datetime.now)

class AccountRequest(Base):
    __tablename__ = "account_requests"
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(BigInteger, nullable=False)
    insta_handle = Column(String(255), nullable=False)
    status = Column(String(50), default='pending')
    created_at = Column(DateTime, default=datetime.now)

class Admin(Base):
    __tablename__ = "admins"
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(BigInteger, nullable=False, unique=True)
    added_by = Column(BigInteger, nullable=False)
    added_at = Column(DateTime, default=datetime.now)

class BannedUser(Base):
    __tablename__ = "banned_users"
    
    user_id = Column(BigInteger, primary_key=True)

class SubmissionLog(Base):
    __tablename__ = "submission_logs"
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(BigInteger, nullable=False)
    shortcode = Column(String(255), nullable=False)
    views = Column(BigInteger, nullable=False)
    old_views = Column(BigInteger, nullable=True)
    insta_handle = Column(String(255), nullable=False)
    action = Column(String(100), nullable=False)
    created_at = Column(DateTime, default=datetime.now)

class ForceUpdateLog(Base):
    __tablename__ = "force_update_logs"
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    total_reels = Column(Integer, nullable=False)
    successful_updates = Column(Integer, nullable=False)
    created_at = Column(DateTime, default=datetime.now)

class SlotAccount(Base):
    __tablename__ = "slot_accounts"
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    slot_number = Column(Integer, nullable=False)
    insta_handle = Column(String(255), nullable=False)
    added_at = Column(DateTime, default=datetime.now)

class SlotSubmission(Base):
    __tablename__ = "slot_submissions"
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    slot_number = Column(Integer, nullable=False)
    shortcode = Column(String(255), nullable=False)
    insta_handle = Column(String(255), nullable=False)
    submitted_at = Column(DateTime, default=datetime.now)
    view_count = Column(BigInteger, default=0)

class Referral(Base):
    __tablename__ = "referrals"
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(BigInteger, nullable=False, unique=True)
    referrer_id = Column(BigInteger, nullable=False)
    created_at = Column(DateTime, default=datetime.now)

class Config(Base):
    __tablename__ = "config"
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    key = Column(String(255), nullable=False, unique=True)
    value = Column(Text, nullable=False)
    created_at = Column(DateTime, default=datetime.now)