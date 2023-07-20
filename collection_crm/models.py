# This is an auto-generated Django model module.
# You'll have to do the following manually to clean this up:
#   * Rearrange models' order
#   * Make sure each model has one field with primary_key=True
#   * Make sure each ForeignKey and OneToOneField has `on_delete` set to the desired behavior
#   * Remove `managed = False` lines if you wish to allow Django to create, modify, and delete the table
# Feel free to rename the models, but don't rename db_table values or field names.
from django.contrib.gis.db import models
from django.contrib.auth.models import User
from django.contrib.postgres.fields import JSONField

from helpline.models import Hotdesk, Schedule, Service


class AllSms(models.Model):
    phone = models.CharField(max_length=250, blank=True, null=True)
    account_name = models.CharField(max_length=255, blank=True, null=True)
    inbound_date = models.DateTimeField(blank=True, null=True)
    dlight_account_no = models.CharField(max_length=255, blank=True, null=True)
    dlight_dealer_no = models.CharField(max_length=255, blank=True, null=True)
    commbased_agent_no = models.CharField(max_length=250, blank=True, null=True)
    sms_content = models.CharField(max_length=250, blank=True, null=True)
    sms_id = models.IntegerField()
    sender = models.CharField(max_length=250, blank=True, null=True)
    receiver = models.CharField(max_length=250, blank=True, null=True)
    contacted = models.CharField(max_length=12)
    batch = models.CharField(max_length=250)
    status = models.TextField()
    sms_category = models.CharField(max_length=50, blank=True, null=True)
    source = models.CharField(max_length=250, blank=True, null=True)
    datetimestamp = models.DateTimeField()
    partial = models.CharField(max_length=1, blank=True, null=True)


class AmeyoDialler(models.Model):
    call_id = models.CharField(max_length=100)
    phone = models.CharField(max_length=30)
    system_disposition = models.CharField(max_length=200)
    user_disposition = models.CharField(max_length=200)
    disposition_date = models.CharField(max_length=100)


class Attempts(models.Model):
    lid = models.CharField(max_length=250)
    phone = models.CharField(max_length=20)
    cs = models.CharField(max_length=100)
    date_done = models.CharField(max_length=20)
    attempt = models.CharField(max_length=20)


class AttemptsList(models.Model):
    name = models.CharField(max_length=20)
    code = models.CharField(max_length=100)


class AuditLogs(models.Model):
    lead_id = models.IntegerField(blank=True, null=True)
    survey_id = models.IntegerField(blank=True, null=True)
    action_date_time = models.DateTimeField()
    audit_action = models.CharField(max_length=16, blank=True, null=True)
    action_before = models.TextField(blank=True, null=True)
    action_after = models.TextField(blank=True, null=True)
    action_user = models.CharField(max_length=100, blank=True, null=True)
    user_ip_address = models.CharField(max_length=255, blank=True, null=True)
    audit_accessed_page = models.TextField(blank=True, null=True)


class Campaign(models.Model):
    client_id = models.IntegerField()
    name = models.CharField(max_length=255)
    created = models.DateTimeField()
    starts = models.DateTimeField(blank=True, null=True)
    ends = models.DateTimeField(blank=True, null=True)
    user_id = models.IntegerField()
    status = models.CharField(max_length=7)


class Clients(models.Model):
    client = models.CharField(max_length=200)
    date_added = models.DateTimeField()
    paybill = models.IntegerField(blank=True, null=True)


class Cronjobs(models.Model):
    task_id = models.BigIntegerField()
    task_name = models.CharField(max_length=255)
    queued_at = models.DateTimeField()
    completed_at = models.DateTimeField()
    is_success = models.CharField(max_length=3)
    status = models.CharField(max_length=9)


class Leads(models.Model):
    idno = models.CharField(max_length=50, blank=True, null=True)
    phone = models.CharField(max_length=250, blank=True, null=True)
    account_name = models.CharField(max_length=255, blank=True, null=True)
    id_number = models.CharField(max_length=200, blank=True, null=True)
    inbound_date = models.DateTimeField(blank=True, null=True)
    dlight_account_no = models.CharField(max_length=255, blank=True, null=True)
    dlight_dealer_no = models.CharField(max_length=255, blank=True, null=True)
    location = models.CharField(max_length=255, blank=True, null=True)
    email = models.CharField(max_length=200, blank=True, null=True)
    branch = models.CharField(max_length=200, blank=True, null=True)
    priority = models.CharField(max_length=250, blank=True, null=True)
    remarks = models.TextField(blank=True, null=True)
    remarks_2 = models.TextField(blank=True, null=True)
    other_phone = models.CharField(max_length=200, blank=True, null=True)
    commbased_agent_no = models.CharField(max_length=250, blank=True, null=True)
    sms_content = models.CharField(max_length=250, blank=True, null=True)
    account_status = models.CharField(max_length=255, blank=True, null=True)
    outstanding_days = models.IntegerField(blank=True, null=True)
    outstanding_amount = models.DecimalField(max_digits=10, decimal_places=2, blank=True, null=True)
    employer = models.CharField(max_length=255, blank=True, null=True)
    salary = models.CharField(max_length=255, blank=True, null=True)
    guarantor_1_name = models.CharField(max_length=200, blank=True, null=True)
    guarantor_1_id = models.CharField(max_length=200, blank=True, null=True)
    guarantor_1_phone = models.CharField(max_length=200, blank=True, null=True)
    guarantor_2_name = models.CharField(max_length=200, blank=True, null=True)
    guarantor_2_id = models.CharField(max_length=200, blank=True, null=True)
    guarantor_2_phone = models.CharField(max_length=200, blank=True, null=True)
    guarantor_3_name = models.CharField(max_length=200, blank=True, null=True)
    guarantor_3_id = models.CharField(max_length=200, blank=True, null=True)
    guarantor_3_phone = models.CharField(max_length=200, blank=True, null=True)
    spouse_1_name = models.CharField(max_length=200, blank=True, null=True)
    spouse_1_id = models.CharField(max_length=200, blank=True, null=True)
    spouse_1_phone = models.CharField(max_length=200, blank=True, null=True)
    postal_address = models.CharField(max_length=255, blank=True, null=True)
    postal_code = models.CharField(max_length=100, blank=True, null=True)
    postal_town = models.CharField(max_length=100, blank=True, null=True)
    customer_client_id = models.CharField(max_length=255, blank=True, null=True)
    sms_id = models.IntegerField(blank=True, null=True)
    sender = models.CharField(max_length=250, blank=True, null=True)
    receiver = models.CharField(max_length=250, blank=True, null=True)
    safaricom_float_target = models.CharField(max_length=200, blank=True, null=True)
    safaricom_commission = models.CharField(max_length=200, blank=True, null=True)
    sanctioned_amount = models.DecimalField(max_digits=10, decimal_places=2, blank=True, null=True)
    sol_id = models.CharField(max_length=20, blank=True, null=True)
    contacted = models.CharField(max_length=12)
    batch = models.CharField(max_length=250, blank=True, null=True)
    status = models.CharField(max_length=100, blank=True, null=True)
    sms_category = models.CharField(max_length=50, blank=True, null=True)
    source = models.CharField(max_length=250, blank=True, null=True)
    datetimestamp = models.DateTimeField()
    partial = models.CharField(max_length=1, blank=True, null=True)
    system_checks = models.CharField(max_length=100, blank=True, null=True)
    done_by = models.CharField(max_length=100, blank=True, null=True)
    call_user = models.CharField(max_length=100, blank=True, null=True)
    client_id = models.IntegerField(blank=True, null=True)
    next_action_date_time = models.CharField(max_length=200, blank=True, null=True)
    last_disposition = models.CharField(max_length=200, blank=True, null=True)
    date_lead_allocated = models.CharField(max_length=25, blank=True, null=True)


class LeadsOrigial(models.Model):
    idno = models.CharField(max_length=50, blank=True, null=True)
    phone = models.CharField(max_length=250, blank=True, null=True)
    account_name = models.CharField(max_length=255, blank=True, null=True)
    inbound_date = models.DateTimeField(blank=True, null=True)
    dlight_account_no = models.CharField(max_length=255, blank=True, null=True)
    dlight_dealer_no = models.CharField(max_length=255, blank=True, null=True)
    priority = models.CharField(max_length=250, blank=True, null=True)
    remarks = models.CharField(max_length=250, blank=True, null=True)
    commbased_agent_no = models.CharField(max_length=250, blank=True, null=True)
    sms_content = models.CharField(max_length=250, blank=True, null=True)
    account_status = models.CharField(max_length=255, blank=True, null=True)
    outstanding_days = models.IntegerField(blank=True, null=True)
    outstanding_amount = models.FloatField(blank=True, null=True)
    sms_id = models.IntegerField()
    sender = models.CharField(max_length=250, blank=True, null=True)
    receiver = models.CharField(max_length=250, blank=True, null=True)
    contacted = models.CharField(max_length=12)
    batch = models.CharField(max_length=250)
    status = models.TextField()
    sms_category = models.CharField(max_length=50, blank=True, null=True)
    source = models.CharField(max_length=250, blank=True, null=True)
    datetimestamp = models.DateTimeField()
    partial = models.CharField(max_length=1, blank=True, null=True)
    system_checks = models.CharField(max_length=100, blank=True, null=True)
    done_by = models.CharField(max_length=100, blank=True, null=True)
    call_user = models.CharField(max_length=100, blank=True, null=True)


class MappingIdNumber(models.Model):
    cf_id = models.CharField(max_length=100, blank=True, null=True)
    id_number = models.CharField(max_length=100, blank=True, null=True)
    email = models.CharField(max_length=200, blank=True, null=True)
    branch = models.CharField(max_length=200, blank=True, null=True)
    account_number = models.CharField(max_length=200, blank=True, null=True)
    name = models.CharField(max_length=200, blank=True, null=True)
    earlier_phone = models.CharField(max_length=200, blank=True, null=True)
    other_phone = models.CharField(max_length=200, blank=True, null=True)
    phone_1 = models.CharField(max_length=200, blank=True, null=True)
    phone_2 = models.CharField(max_length=200, blank=True, null=True)
    phone_3 = models.CharField(max_length=200, blank=True, null=True)
    phone_4 = models.CharField(max_length=200, blank=True, null=True)
    phone_5 = models.CharField(max_length=200, blank=True, null=True)
    phone_6 = models.CharField(max_length=200, blank=True, null=True)
    phone_7 = models.CharField(max_length=200, blank=True, null=True)
    phone_8 = models.CharField(max_length=200, blank=True, null=True)
    next_action_date_time = models.CharField(max_length=200, blank=True, null=True)
    call_user = models.CharField(max_length=200, blank=True, null=True)


class OutboundSms(models.Model):
    receiver = models.CharField(max_length=15)
    message = models.TextField()
    time = models.DateTimeField()
    api_feedback = models.TextField(blank=True, null=True)
    status = models.IntegerField()
    batch = models.CharField(max_length=255, blank=True, null=True)
    scheduled_time = models.CharField(max_length=255, blank=True, null=True)
    sent_status = models.CharField(max_length=255, blank=True, null=True)
    lead_id = models.CharField(max_length=255, blank=True, null=True)
    phone = models.CharField(max_length=255, blank=True, null=True)
    username = models.CharField(max_length=255, blank=True, null=True)


class Outlets(models.Model):
    idno = models.CharField(max_length=50, blank=True, null=True)
    businessname = models.CharField(max_length=250, blank=True, null=True)
    county = models.CharField(max_length=255, blank=True, null=True)
    locationdescription = models.CharField(max_length=250, blank=True, null=True)
    phone = models.CharField(max_length=255, blank=True, null=True)
    staffrepresentative = models.CharField(max_length=255, blank=True, null=True)
    datetimestamp = models.DateTimeField()


class QcData(models.Model):
    lid = models.IntegerField()
    interviewer = models.CharField(max_length=200)
    cs = models.CharField(max_length=10)
    q1 = models.TextField(db_column='Q1')  # Field name made lowercase.
    q2 = models.CharField(db_column='Q2', max_length=50)  # Field name made lowercase.
    q3 = models.CharField(db_column='Q3', max_length=50)  # Field name made lowercase.
    q4 = models.CharField(db_column='Q4', max_length=50)  # Field name made lowercase.
    q5 = models.TextField(db_column='Q5')  # Field name made lowercase.
    q5a = models.CharField(db_column='Q5a', max_length=250, blank=True, null=True)  # Field name made lowercase.
    q5o = models.CharField(db_column='Q5o', max_length=250, blank=True, null=True)  # Field name made lowercase.
    q6 = models.TextField(db_column='Q6')  # Field name made lowercase.
    q7 = models.TextField(db_column='Q7')  # Field name made lowercase.
    q7_text = models.CharField(db_column='Q7_text', max_length=250, blank=True, null=True)  # Field name made lowercase.
    q8 = models.TextField(db_column='Q8')  # Field name made lowercase.
    q9 = models.TextField(db_column='Q9')  # Field name made lowercase.
    q9a = models.CharField(db_column='Q9a', max_length=250, blank=True, null=True)  # Field name made lowercase.
    other1 = models.CharField(max_length=250, blank=True, null=True)
    other2 = models.CharField(max_length=250, blank=True, null=True)
    q10 = models.TextField(db_column='Q10')  # Field name made lowercase.
    q11 = models.TextField(db_column='Q11')  # Field name made lowercase.
    q12 = models.TextField(db_column='Q12')  # Field name made lowercase.
    q13 = models.TextField(db_column='Q13')  # Field name made lowercase.
    q14 = models.TextField(db_column='Q14')  # Field name made lowercase.
    q15 = models.TextField(db_column='Q15')  # Field name made lowercase.
    q16 = models.TextField(db_column='Q16')  # Field name made lowercase.
    q17 = models.TextField(db_column='Q17')  # Field name made lowercase.
    q18 = models.TextField(db_column='Q18')  # Field name made lowercase.
    q18a = models.CharField(db_column='Q18a', max_length=250, blank=True, null=True)  # Field name made lowercase.
    other_1 = models.CharField(max_length=250, blank=True, null=True)
    other_2 = models.CharField(max_length=250, blank=True, null=True)
    q19 = models.TextField(db_column='Q19')  # Field name made lowercase.
    q20 = models.TextField(db_column='Q20')  # Field name made lowercase.
    q21 = models.TextField(db_column='Q21')  # Field name made lowercase.
    q22 = models.TextField(db_column='Q22')  # Field name made lowercase.
    q22a = models.CharField(db_column='Q22a', max_length=250, blank=True, null=True)  # Field name made lowercase.
    q22b = models.CharField(db_column='Q22b', max_length=250, blank=True, null=True)  # Field name made lowercase.
    q22c = models.CharField(db_column='Q22c', max_length=250, blank=True, null=True)  # Field name made lowercase.
    q23 = models.TextField(db_column='Q23')  # Field name made lowercase.
    q24 = models.TextField(db_column='Q24')  # Field name made lowercase.
    q25 = models.TextField(db_column='Q25')  # Field name made lowercase.
    q26 = models.TextField(db_column='Q26')  # Field name made lowercase.
    q27 = models.TextField(db_column='Q27')  # Field name made lowercase.
    q28 = models.TextField(db_column='Q28')  # Field name made lowercase.
    q29 = models.TextField(db_column='Q29')  # Field name made lowercase.
    q29a = models.CharField(db_column='Q29a', max_length=250, blank=True, null=True)  # Field name made lowercase.
    q29_other = models.CharField(db_column='Q29_other', max_length=250, blank=True, null=True)  # Field name made lowercase.
    q29_other2 = models.CharField(db_column='Q29_other2', max_length=250, blank=True, null=True)  # Field name made lowercase.
    q30 = models.TextField(db_column='Q30')  # Field name made lowercase.
    q31 = models.TextField(db_column='Q31')  # Field name made lowercase.
    q32 = models.TextField(db_column='Q32')  # Field name made lowercase.
    q33 = models.TextField(db_column='Q33')  # Field name made lowercase.
    q34 = models.TextField(db_column='Q34')  # Field name made lowercase.
    q35 = models.TextField(db_column='Q35')  # Field name made lowercase.
    q36 = models.TextField(db_column='Q36')  # Field name made lowercase.
    q37 = models.TextField(db_column='Q37')  # Field name made lowercase.
    q38 = models.TextField(db_column='Q38')  # Field name made lowercase.
    q39 = models.TextField(db_column='Q39')  # Field name made lowercase.
    q40 = models.TextField(db_column='Q40')  # Field name made lowercase.
    q41 = models.TextField(db_column='Q41')  # Field name made lowercase.
    q42 = models.TextField(db_column='Q42')  # Field name made lowercase.
    q43 = models.TextField(db_column='Q43')  # Field name made lowercase.
    q44 = models.TextField(db_column='Q44')  # Field name made lowercase.
    q45 = models.TextField(db_column='Q45')  # Field name made lowercase.
    q46 = models.TextField(db_column='Q46')  # Field name made lowercase.
    q47 = models.TextField(db_column='Q47')  # Field name made lowercase.
    q48 = models.TextField(db_column='Q48')  # Field name made lowercase.
    q49 = models.TextField(db_column='Q49')  # Field name made lowercase.
    q50 = models.TextField(db_column='Q50')  # Field name made lowercase.
    q51 = models.TextField(db_column='Q51')  # Field name made lowercase.
    q52 = models.TextField(db_column='Q52')  # Field name made lowercase.
    q53 = models.TextField(db_column='Q53')  # Field name made lowercase.
    q54 = models.TextField(db_column='Q54')  # Field name made lowercase.
    q55 = models.TextField(db_column='Q55')  # Field name made lowercase.
    q56 = models.TextField(db_column='Q56')  # Field name made lowercase.
    q57 = models.TextField(db_column='Q57')  # Field name made lowercase.
    q58 = models.TextField(db_column='Q58')  # Field name made lowercase.
    q59 = models.TextField(db_column='Q59')  # Field name made lowercase.
    q60 = models.TextField(db_column='Q60')  # Field name made lowercase.
    q61 = models.TextField(db_column='Q61')  # Field name made lowercase.
    q62 = models.TextField(db_column='Q62')  # Field name made lowercase.
    q63 = models.TextField(db_column='Q63')  # Field name made lowercase.
    q64 = models.TextField(db_column='Q64')  # Field name made lowercase.
    q65 = models.TextField(db_column='Q65')  # Field name made lowercase.
    q66 = models.TextField(db_column='Q66')  # Field name made lowercase.
    q67 = models.TextField(db_column='Q67')  # Field name made lowercase.
    q68 = models.TextField(db_column='Q68')  # Field name made lowercase.
    q69 = models.TextField(db_column='Q69')  # Field name made lowercase.
    q70 = models.TextField(db_column='Q70')  # Field name made lowercase.
    q71 = models.TextField(db_column='Q71')  # Field name made lowercase.
    q72 = models.TextField(db_column='Q72')  # Field name made lowercase.
    q73 = models.TextField(db_column='Q73')  # Field name made lowercase.
    q74 = models.TextField(db_column='Q74')  # Field name made lowercase.
    q75 = models.TextField(db_column='Q75')  # Field name made lowercase.
    q76 = models.TextField(db_column='Q76')  # Field name made lowercase.
    q77 = models.TextField(db_column='Q77')  # Field name made lowercase.
    q78 = models.TextField(db_column='Q78')  # Field name made lowercase.
    q79 = models.TextField(db_column='Q79')  # Field name made lowercase.
    q80 = models.TextField(db_column='Q80')  # Field name made lowercase.
    q81 = models.TextField(db_column='Q81')  # Field name made lowercase.
    lang = models.CharField(max_length=50, blank=True, null=True)
    phone = models.CharField(max_length=255)
    farmer = models.CharField(max_length=255, blank=True, null=True)
    id_number = models.CharField(max_length=200)
    gender = models.CharField(max_length=200, blank=True, null=True)
    clinic_visited = models.CharField(max_length=255, blank=True, null=True)
    date_visited = models.CharField(max_length=50, blank=True, null=True)
    crop = models.CharField(max_length=200, blank=True, null=True)
    callbacktime = models.CharField(max_length=200)
    disposition = models.TextField()
    disptype = models.TextField()
    date = models.DateTimeField()
    start_time = models.CharField(max_length=200)
    stop_time = models.CharField(max_length=50)
    last_page = models.CharField(max_length=250, blank=True, null=True)
    redial_times = models.IntegerField()


class Qcfiles(models.Model):
    qcid = models.IntegerField(blank=True, null=True)
    par1 = models.IntegerField(blank=True, null=True)
    par2 = models.IntegerField(blank=True, null=True)
    par3 = models.IntegerField(blank=True, null=True)
    par4 = models.IntegerField(blank=True, null=True)
    par5 = models.IntegerField(blank=True, null=True)
    par6 = models.IntegerField(blank=True, null=True)
    par7 = models.IntegerField(blank=True, null=True)
    par8 = models.IntegerField(blank=True, null=True)
    par9 = models.IntegerField(blank=True, null=True)
    par10 = models.IntegerField(blank=True, null=True)
    par11 = models.IntegerField(blank=True, null=True)
    par12 = models.IntegerField(blank=True, null=True)
    par13 = models.IntegerField(blank=True, null=True)
    par14 = models.IntegerField(blank=True, null=True)
    par15 = models.IntegerField(blank=True, null=True)
    par16 = models.IntegerField(blank=True, null=True)
    par17 = models.IntegerField(blank=True, null=True)
    par18 = models.IntegerField(blank=True, null=True)
    par19 = models.IntegerField(blank=True, null=True)
    par20 = models.IntegerField(blank=True, null=True)
    par21 = models.IntegerField(blank=True, null=True)
    par22 = models.IntegerField(blank=True, null=True)
    par23 = models.IntegerField(blank=True, null=True)
    processor = models.CharField(max_length=100, blank=True, null=True)
    customername = models.CharField(max_length=100, blank=True, null=True)
    supervisor = models.CharField(max_length=100, blank=True, null=True)
    auditor = models.CharField(max_length=100, blank=True, null=True)
    transactiondate = models.DateField(blank=True, null=True)
    samaid = models.CharField(max_length=10, blank=True, null=True)
    phoneno = models.CharField(max_length=100, blank=True, null=True)
    qadate = models.DateField(blank=True, null=True)
    comments = models.CharField(max_length=2000, blank=True, null=True)
    qualitypassed = models.CharField(max_length=20, blank=True, null=True)
    totalmarks = models.IntegerField(blank=True, null=True)
    qamarks = models.IntegerField(blank=True, null=True)
    asof = models.DateTimeField()


class Queue(models.Model):
    task_id = models.IntegerField()
    lead_id = models.IntegerField(blank=True, null=True)
    msisdn = models.CharField(max_length=16)
    account_name = models.CharField(max_length=255)
    client = models.CharField(max_length=255)
    client_paybill = models.IntegerField()
    balance = models.FloatField()
    sms = models.CharField(max_length=160)
    uuid = models.CharField(max_length=64)


class Sms(models.Model):
    task_id = models.IntegerField(blank=True, null=True)
    lead_id = models.IntegerField(blank=True, null=True)
    uuid = models.CharField(max_length=255)
    msisdn = models.BigIntegerField()
    body = models.TextField()
    queued = models.DateTimeField()
    sent = models.DateTimeField(blank=True, null=True)
    response_code = models.IntegerField()
    response_description = models.CharField(max_length=48)
    message_id = models.CharField(max_length=255)
    request_id = models.CharField(max_length=255)
    service_id = models.IntegerField()
    total_addresses = models.IntegerField()
    credit_units = models.FloatField()
    credit_unit_balance = models.FloatField()
    transaction_status = models.CharField(max_length=255)
    status = models.CharField(max_length=9)


class SmsCallbacks(models.Model):
    message_id = models.CharField(max_length=255)
    correlator = models.CharField(max_length=255)
    delivery_status = models.CharField(max_length=255)
    api_timestamp = models.CharField(max_length=255)
    msisdn = models.BigIntegerField()
    created = models.DateTimeField()


class SmsProvider(models.Model):
    client_id = models.IntegerField(blank=True, null=True)
    user_id = models.IntegerField(blank=True, null=True)
    name = models.CharField(max_length=255)
    username = models.CharField(max_length=255)
    password = models.CharField(max_length=255)
    created = models.DateTimeField()
    url = models.CharField(max_length=255)
    is_default = models.IntegerField()
    status = models.CharField(max_length=3)


class SmsTask(models.Model):
    client_id = models.IntegerField()
    campaign_id = models.IntegerField()
    task_type_id = models.IntegerField()
    created = models.DateTimeField()
    scheduled = models.DateTimeField()
    started = models.DateTimeField()
    completed = models.DateTimeField()
    first_lead_id = models.IntegerField()
    last_lead_id = models.IntegerField()
    records = models.IntegerField()
    status = models.CharField(max_length=9)
    user_id = models.IntegerField()


class SmsTaskType(models.Model):
    user_id = models.IntegerField()
    name = models.CharField(max_length=255)
    created = models.DateTimeField()
    is_scheduled = models.IntegerField()
    runtime = models.TimeField()
    retries = models.TimeField()
    dow = models.CharField(max_length=32)
    status = models.CharField(max_length=3)


class SmsTemplate(models.Model):
    client_id = models.IntegerField()
    campaign_id = models.IntegerField(blank=True, null=True)
    user_id = models.IntegerField(blank=True, null=True)
    name = models.CharField(max_length=255)
    description = models.TextField()
    created = models.DateTimeField()
    status = models.CharField(max_length=8)


class SmsTemplates(models.Model):
    template_name = models.CharField(max_length=200)
    template_description = models.TextField()
    client_id = models.IntegerField()


class StateTbl(models.Model):
    s_id = models.CharField(max_length=20)
    match_done = models.CharField(max_length=100)
    s_date = models.CharField(max_length=20)
    date_timestamp = models.DateTimeField()


class Status(models.Model):
    status = models.CharField(max_length=200, blank=True, null=True)


class Survey(models.Model):
    lid = models.IntegerField()
    sms_content = models.TextField(blank=True, null=True)
    sender = models.CharField(max_length=200, blank=True, null=True)
    inbound_date = models.CharField(max_length=250, blank=True, null=True)
    next_call_time = models.CharField(max_length=250, blank=True, null=True)
    tat = models.CharField(max_length=250, blank=True, null=True)
    reference = models.CharField(max_length=250)
    stage = models.CharField(max_length=250)
    interviewer = models.CharField(max_length=200)
    cs = models.CharField(max_length=10)
    q1 = models.CharField(db_column='Q1', blank=True, null=True, max_length=250)
    q2 = models.CharField(db_column='Q2', blank=True, null=True, max_length=250)
    q3 = models.CharField(db_column='Q3', blank=True, null=True, max_length=250)
    q4 = models.CharField(db_column='Q4', blank=True, null=True, max_length=250)
    firstname = models.CharField(max_length=100, blank=True, null=True)
    lastname = models.CharField(max_length=100, blank=True, null=True)
    q1_a = models.CharField(db_column='Q1_a', max_length=100, blank=True, null=True)  # Field name made lowercase.
    q2_a = models.CharField(db_column='Q2_a', max_length=100, blank=True, null=True)  # Field name made lowercase.
    q2_a_other = models.CharField(db_column='Q2_a_other', max_length=250, blank=True, null=True)  # Field name made lowercase.
    purchase_dlight = models.CharField(max_length=100, blank=True, null=True)
    dlight_product = models.CharField(max_length=100, blank=True, null=True)
    q5_1 = models.CharField(db_column='Q5_1', max_length=250, blank=True, null=True)  # Field name made lowercase.
    purchase_date = models.CharField(max_length=100, blank=True, null=True)
    county = models.CharField(max_length=200, blank=True, null=True)
    location = models.CharField(max_length=200, blank=True, null=True)
    outlet = models.CharField(max_length=200, blank=True, null=True)
    outletphone = models.CharField(max_length=250, blank=True, null=True)
    lang = models.CharField(max_length=50, blank=True, null=True)
    phone = models.CharField(max_length=255)
    farmer = models.CharField(max_length=255, blank=True, null=True)
    id_number = models.CharField(max_length=200, blank=True, null=True)
    gender = models.CharField(max_length=200, blank=True, null=True)
    clinic_visited = models.CharField(max_length=255, blank=True, null=True)
    date_visited = models.CharField(max_length=50, blank=True, null=True)
    received_sms = models.CharField(max_length=250, blank=True, null=True)
    crop = models.CharField(max_length=200, blank=True, null=True)
    l1_remark = models.CharField(max_length=200, blank=True, null=True)
    date_of_payment = models.CharField(max_length=200, blank=True, null=True)
    amount_paid = models.IntegerField(blank=True, null=True)
    l2_remark = models.CharField(max_length=200, blank=True, null=True)
    unit_given_to_dealer = models.CharField(max_length=200, blank=True, null=True)
    real_customer_name = models.CharField(max_length=200, blank=True, null=True)
    real_customer_contact = models.CharField(max_length=200, blank=True, null=True)
    not_given_to_dealer = models.CharField(max_length=200, blank=True, null=True)
    tentative_date_of_payment = models.CharField(max_length=100, blank=True, null=True)
    tentative_time_of_payment = models.CharField(max_length=100, blank=True, null=True)
    tentative_amount_of_payment = models.CharField(max_length=100, blank=True, null=True)
    tentative_date_of_decision = models.CharField(max_length=100, blank=True, null=True)
    reason_not_going_to_pay = models.CharField(max_length=255, blank=True, null=True)
    reason_not_going_to_pay_other = models.TextField(blank=True, null=True)
    unit_given_to_dealer_date = models.CharField(max_length=250, blank=True, null=True)
    unit_given_to_dealer_name = models.CharField(max_length=250, blank=True, null=True)
    other = models.CharField(max_length=250, blank=True, null=True)
    other_number = models.CharField(max_length=250, blank=True, null=True)
    other_comment = models.TextField(blank=True, null=True)
    callbacktime = models.CharField(max_length=200)
    disposition = models.CharField(max_length=250, blank=True, null=True)
    comment = models.TextField(blank=True, null=True)
    tentative_date_of_payment_not_provide = models.CharField(max_length=200, blank=True, null=True)
    tentative_date_of_decision_not_provide = models.CharField(max_length=200, blank=True, null=True)
    disptype = models.TextField()
    batch = models.IntegerField()
    date = models.DateTimeField()
    duplicate_date = models.CharField(max_length=250)
    start_time = models.CharField(max_length=200)
    stop_time = models.CharField(max_length=50)
    last_page = models.CharField(max_length=250, blank=True, null=True)
    redial_times = models.IntegerField()
    audio_match = models.CharField(max_length=250)
    audio_match_by = models.CharField(max_length=250)
    quality = models.CharField(max_length=250)
    quality_by = models.CharField(max_length=250)
    call_back_later = models.PositiveIntegerField()
    non_payment_reason = models.CharField(max_length=255, blank=True, null=True)
    unit_given_to_dealer_contact = models.CharField(max_length=255)
    next_action_date_time = models.CharField(max_length=200, blank=True, null=True)
    data = JSONField(default=dict, null=True, blank=True)


class SurveyOld(models.Model):
    lid = models.IntegerField()
    reference = models.CharField(max_length=250)
    stage = models.CharField(max_length=250)
    interviewer = models.CharField(max_length=200)
    cs = models.CharField(max_length=10)
    q1 = models.CharField(db_column='Q1', max_length=100, blank=True, null=True)  # Field name made lowercase.
    q2 = models.CharField(db_column='Q2', max_length=100, blank=True, null=True)  # Field name made lowercase.
    q3 = models.CharField(db_column='Q3', max_length=100, blank=True, null=True)  # Field name made lowercase.
    q4 = models.CharField(db_column='Q4', max_length=100, blank=True, null=True)  # Field name made lowercase.
    lang = models.CharField(max_length=50, blank=True, null=True)
    crop = models.CharField(max_length=100, blank=True, null=True)
    phone = models.CharField(max_length=255)
    farmer = models.CharField(max_length=255, blank=True, null=True)
    id_number = models.CharField(max_length=200, blank=True, null=True)
    gender = models.CharField(max_length=200, blank=True, null=True)
    clinic_visited = models.CharField(max_length=255, blank=True, null=True)
    date_visited = models.CharField(max_length=50, blank=True, null=True)
    callbacktime = models.CharField(max_length=200)
    disposition = models.TextField()
    disptype = models.TextField()
    batch = models.IntegerField(blank=True, null=True)
    date = models.DateTimeField()
    duplicate_date = models.CharField(max_length=250)
    start_time = models.CharField(max_length=200)
    inbound_date = models.DateTimeField(blank=True, null=True)
    stop_time = models.CharField(max_length=50)
    tat = models.CharField(max_length=250, blank=True, null=True)
    next_call_time = models.DateTimeField()
    datemail = models.DateField()
    last_page = models.CharField(max_length=250, blank=True, null=True)
    redial_times = models.IntegerField()
    audio_match = models.CharField(max_length=250)
    audio_match_by = models.CharField(max_length=250)
    quality = models.CharField(max_length=250)
    quality_by = models.CharField(max_length=250)


class Task(models.Model):
    client_id = models.IntegerField(blank=True, null=True)
    campaign_id = models.IntegerField(blank=True, null=True)
    template_id = models.IntegerField(blank=True, null=True)
    uuid = models.CharField(max_length=255)
    task_type = models.CharField(max_length=255)
    name = models.CharField(max_length=255)
    created = models.DateTimeField()
    scheduled = models.DateTimeField()
    started = models.DateTimeField(blank=True, null=True)
    completed = models.DateTimeField(blank=True, null=True)
    failed = models.DateTimeField(blank=True, null=True)
    first_lead_id = models.IntegerField(blank=True, null=True)
    last_lead_id = models.IntegerField(blank=True, null=True)
    records = models.IntegerField(blank=True, null=True)
    status = models.CharField(max_length=9)
    user_id = models.IntegerField(blank=True, null=True)


class CollectionUser(models.Model):
    """Collection CRM Users"""
    AGENT = 'agent'
    SUPERVISOR = 'supervisor'
    ADMINISTRATOR = 'administrator'
    USER_LEVEL_CHOICES = (
        (AGENT, 'Agent'),
        (SUPERVISOR, 'Supervisor'),
        (ADMINISTRATOR, 'Administrator'),
    )
    ACTIVE = 'active'
    SUSPENDED = 'suspended'
    ACCOUNT_STATUS_CHOICES = (
        (ACTIVE, 'Active'),
        (SUSPENDED, 'Suspended'),
    )
    CRM_AND_TELEPHONY = 'crm_and_telephony'
    CRM_ONLY = 'crm_only'
    TELEPHONY_ONLY = 'telephony_only'
    SYSTEM_ACCESS_CHOICES = (
        (CRM_AND_TELEPHONY, 'CRM and Telephony'),
        (CRM_ONLY, 'CRM Only'),
        (TELEPHONY_ONLY, 'Telephony Only'),
    )

    user = models.OneToOneField(
        User, on_delete=models.CASCADE,
        related_name='CollectionUser'
    )

    level = models.CharField(
        max_length=100,
        choices=USER_LEVEL_CHOICES,
        blank=True,
        null=True,
        default=AGENT,
    )
    telephony = models.CharField(max_length=255, blank=True, null=True)
    extension_number = models.CharField(max_length=20, blank=True, null=True)
    systems_access = models.CharField(
        choices=SYSTEM_ACCESS_CHOICES,
        max_length=255,
        blank=True,
        null=True,
        default=CRM_AND_TELEPHONY,
    )
    assigned_queue = models.CharField(max_length=255, blank=True, null=True)
    account_status = models.CharField(
        max_length=20,
        choices=ACCOUNT_STATUS_CHOICES,
        default=ACTIVE,
        blank=True,
        null=True
    )
    daily_target = models.IntegerField(blank=True, null=True)
    monthly_target = models.IntegerField(blank=True, null=True)
