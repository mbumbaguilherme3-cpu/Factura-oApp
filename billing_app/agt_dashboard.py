"""
AGT Dashboard Web Routes
Fornece interface web para visualização e gestão de faturas
"""

from flask import Blueprint, render_template, request
from datetime import datetime, timedelta
from decimal import Decimal

from billing_app.db_config import db
from billing_app.agt_models import Invoice, AGTComplianceLog, InvoiceSignatureAudit, AnyEntity

# Create Blueprint
agt_dashboard = Blueprint('dashboard', __name__, url_prefix='/dashboard')


@agt_dashboard.route('/', methods=['GET'])
def index():
    """Main dashboard"""
    
    # Get statistics
    today = datetime.now().date()
    month_start = datetime(today.year, today.month, 1)
    
    # Invoices this month
    invoices_this_month = db.session.query(Invoice).filter(
        Invoice.invoice_date >= month_start,
        Invoice.deleted_at.is_(None)
    ).count()
    
    # Total amounts
    totals = db.session.query(
        db.func.sum(Invoice.gross_total),
        db.func.sum(Invoice.iva_total)
    ).filter(
        Invoice.invoice_date >= month_start,
        Invoice.is_issued == True,
        Invoice.deleted_at.is_(None)
    ).first()
    
    total_amount = totals[0] or Decimal('0.00')
    total_iva = totals[1] or Decimal('0.00')
    
    # Issued invoices
    issued_count = db.session.query(Invoice).filter(
        Invoice.is_issued == True,
        Invoice.deleted_at.is_(None)
    ).count()
    
    # Pending AGT
    pending_agt = db.session.query(Invoice).filter(
        Invoice.status.in_(['S', 'T']),  # SIGNED or SUBMITTED
        Invoice.agt_submission_id.is_(None),
        Invoice.deleted_at.is_(None)
    ).count()
    
    # Compliance percentage
    total_events = db.session.query(AGTComplianceLog).filter(
        AGTComplianceLog.created_at >= datetime.now() - timedelta(days=30)
    ).count()
    
    compliant_events = db.session.query(AGTComplianceLog).filter(
        AGTComplianceLog.is_compliant == True,
        AGTComplianceLog.created_at >= datetime.now() - timedelta(days=30)
    ).count()
    
    compliance_percentage = int((compliant_events / total_events * 100) if total_events > 0 else 100)
    
    stats = {
        'invoices_this_month': invoices_this_month,
        'total_amount': total_amount,
        'total_iva': total_iva,
        'issued_invoices': issued_count,
        'pending_agt': pending_agt,
        'compliance_percentage': compliance_percentage
    }
    
    # Recent invoices
    recent_invoices = db.session.query(Invoice).filter(
        Invoice.deleted_at.is_(None)
    ).order_by(Invoice.created_at.desc()).limit(10).all()
    
    # Add customer names
    for inv in recent_invoices:
        customer = db.session.query(AnyEntity).filter_by(entity_id=inv.customer_id).first()
        inv.customer_name = customer.name if customer else 'Unknown'
    
    # Daily amounts (last 7 days)
    daily_amounts = []
    for i in range(6, -1, -1):
        day = today - timedelta(days=i)
        amount = db.session.query(
            db.func.sum(Invoice.gross_total)
        ).filter(
            Invoice.invoice_date >= datetime(day.year, day.month, day.day),
            Invoice.invoice_date < datetime(day.year, day.month, day.day) + timedelta(days=1),
            Invoice.is_issued == True,
            Invoice.deleted_at.is_(None)
        ).first()
        daily_amounts.append(float(amount[0] or 0))
    
    # IVA distribution
    general_count = db.session.query(db.func.count()).filter(
        Invoice.status.in_(['I', 'S', 'T', 'A']),
        Invoice.deleted_at.is_(None)
    ).scalar()
    
    iva_distribution = [general_count, 0, 0]  # Simplified
    
    # System status
    system_status = {
        'keys_available': True,  # Would check /etc/ssl/agt/
        'agt_connected': True    # Would ping AGT API
    }
    
    return render_template('dashboard.html',
        stats=stats,
        recent_invoices=recent_invoices,
        daily_amounts=daily_amounts,
        iva_distribution=iva_distribution,
        system_status=system_status
    )


@agt_dashboard.route('/invoices', methods=['GET'])
def invoices():
    """Invoices management page"""
    
    page = request.args.get('page', 1, type=int)
    per_page = 20
    
    query = db.session.query(Invoice).filter(Invoice.deleted_at.is_(None))
    
    # Filter by status
    status = request.args.get('status')
    if status:
        query = query.filter_by(status=status)
    
    # Filter by period
    period = request.args.get('period')
    if period == 'today':
        today = datetime.now().date()
        query = query.filter(
            Invoice.invoice_date >= datetime(today.year, today.month, today.day),
            Invoice.invoice_date < datetime(today.year, today.month, today.day) + timedelta(days=1)
        )
    elif period == 'this-week':
        today = datetime.now().date()
        start = today - timedelta(days=today.weekday())
        query = query.filter(Invoice.invoice_date >= datetime(start.year, start.month, start.day))
    elif period == 'this-month':
        today = datetime.now().date()
        query = query.filter(Invoice.invoice_date >= datetime(today.year, today.month, 1))
    
    total = query.count()
    invoices_list = query.order_by(Invoice.created_at.desc()).offset((page - 1) * per_page).limit(per_page).all()
    
    # Add customer names
    for inv in invoices_list:
        customer = db.session.query(AnyEntity).filter_by(entity_id=inv.customer_id).first()
        inv.customer_name = customer.name if customer else 'Unknown'
    
    total_pages = (total + per_page - 1) // per_page
    page_numbers = range(1, total_pages + 1)
    
    return render_template('invoices.html',
        invoices=invoices_list,
        current_page=page,
        total_pages=total_pages,
        page_numbers=page_numbers
    )


@agt_dashboard.route('/compliance', methods=['GET'])
def compliance():
    """Compliance and audit page"""
    
    # Compliance statistics
    last_month = datetime.now() - timedelta(days=30)
    
    total_events = db.session.query(AGTComplianceLog).filter(
        AGTComplianceLog.created_at >= last_month
    ).count()
    
    compliant_events = db.session.query(AGTComplianceLog).filter(
        AGTComplianceLog.is_compliant == True,
        AGTComplianceLog.created_at >= last_month
    ).count()
    
    non_compliant = total_events - compliant_events
    
    compliance_rate = int((compliant_events / total_events * 100) if total_events > 0 else 100)
    
    # Failed validations
    failed_validations = db.session.query(AGTComplianceLog).filter(
        AGTComplianceLog.is_compliant == False,
        AGTComplianceLog.created_at >= datetime.now() - timedelta(hours=24)
    ).count()
    
    compliance_stats = {
        'rate': compliance_rate,
        'total_events': total_events,
        'non_compliant_events': non_compliant,
        'failed_validations': failed_validations
    }
    
    # Compliance alerts
    alerts = db.session.query(AGTComplianceLog).filter(
        AGTComplianceLog.is_compliant == False
    ).order_by(AGTComplianceLog.created_at.desc()).limit(5).all()
    
    compliance_alerts = []
    for alert in alerts:
        compliance_alerts.append({
            'title': alert.event_type,
            'message': alert.compliance_notes or alert.details or 'Sem detalhes',
            'severity': 'error' if alert.is_compliant == False else 'warning',
            'timestamp': alert.created_at
        })
    
    # Audit logs
    audit_logs = db.session.query(AGTComplianceLog).order_by(
        AGTComplianceLog.created_at.desc()
    ).limit(50).all()
    
    # Signature audits
    signature_audits = db.session.query(InvoiceSignatureAudit).order_by(
        InvoiceSignatureAudit.created_at.desc()
    ).limit(50).all()
    
    return render_template('compliance.html',
        compliance_stats=compliance_stats,
        compliance_alerts=compliance_alerts,
        audit_logs=audit_logs,
        signature_audits=signature_audits
    )
