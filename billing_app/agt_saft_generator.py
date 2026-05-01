"""
SAF-T (AO) XML Generator - Angola
Generates SAF-T format XML files for AGT compliance
Reference: SAF-T (AO) v1.05 specification
"""

from datetime import datetime
from decimal import Decimal
from typing import Dict, List, Optional, Any
from xml.etree.ElementTree import Element, SubElement, tostring
from xml.dom import minidom


class SAFTAOGenerator:
    """
    Generates SAF-T (AO) XML format for AGT compliance
    
    Structure:
    - AuditFile (root)
        - Header
        - MasterFiles
            - Customer
            - Product
        - SourceDocuments
            - SalesInvoices
            - CreditNotes
            - DebitNotes
    """
    
    # SAF-T AO namespace and schema location
    NAMESPACE = "urn:OECD:StandardAuditFile-Tax:AO_1.05_01"
    SCHEMA_LOCATION = "https://www.agt.gov.ao/portal/schemas/saft-ao_1_05_01.xsd"
    
    def __init__(self, company_data: Dict[str, Any], version: str = "1.05_01"):
        """
        Initialize SAF-T generator
        
        Args:
            company_data: Company information for header
            version: SAF-T version (default 1.05_01)
        """
        self.company_data = company_data
        self.version = version
        self.root = None
        self.header = None
    
    def generate(
        self,
        customers: List[Dict[str, Any]],
        products: List[Dict[str, Any]],
        invoices: List[Dict[str, Any]],
        credit_notes: List[Dict[str, Any]] = None,
        debit_notes: List[Dict[str, Any]] = None
    ) -> str:
        """
        Generate complete SAF-T (AO) XML
        
        Args:
            customers: List of customer entities
            products: List of products
            invoices: List of invoices
            credit_notes: Optional list of credit notes
            debit_notes: Optional list of debit notes
            
        Returns:
            XML string
        """
        
        # Create root element
        self.root = Element('AuditFile')
        self.root.set('xmlns', self.NAMESPACE)
        self.root.set('{http://www.w3.org/2001/XMLSchema-instance}schemaLocation', 
                      f"{self.NAMESPACE} {self.SCHEMA_LOCATION}")
        
        # Build sections
        self._build_header()
        self._build_master_files(customers, products)
        self._build_source_documents(invoices, credit_notes, debit_notes)
        
        return self._format_xml()
    
    def _build_header(self) -> None:
        """Build AuditFile Header section"""
        
        header = SubElement(self.root, 'Header')
        
        # Audit File Identification
        self._add_element(header, 'AuditFileVersion', self.version)
        self._add_element(header, 'AuditFileCountry', 'AO')  # Angola
        self._add_element(header, 'AuditFileDateCreated', datetime.utcnow().isoformat())
        self._add_element(header, 'AuditFileTimeCreated', datetime.utcnow().isoformat())
        
        # Company Information
        company = SubElement(header, 'Company')
        self._add_element(company, 'RegistrationNumber', self.company_data.get('nif', ''))
        self._add_element(company, 'Name', self.company_data.get('name', ''))
        
        # Address
        address = SubElement(company, 'Address')
        self._add_element(address, 'AddressDetail', self.company_data.get('address_detail', ''))
        self._add_element(address, 'City', self.company_data.get('city', ''))
        self._add_element(address, 'PostalCode', self.company_data.get('postal_code', ''))
        self._add_element(address, 'Country', 'AO')
        
        # Contact information
        self._add_element(company, 'Telephone', self.company_data.get('telephone', ''))
        self._add_element(company, 'Fax', self.company_data.get('fax', ''))
        self._add_element(company, 'Email', self.company_data.get('email', ''))
        
        # Tax Accountant (optional but recommended)
        tax_contact = SubElement(header, 'TaxContacts')
        tax_contact_person = SubElement(tax_contact, 'TaxContact')
        self._add_element(tax_contact_person, 'ContactName', self.company_data.get('tax_contact_name', ''))
        self._add_element(tax_contact_person, 'Telephone', self.company_data.get('tax_contact_phone', ''))
        self._add_element(tax_contact_person, 'Email', self.company_data.get('tax_contact_email', ''))
        
        # File signature (placeholder for JWS signature)
        self._add_element(header, 'FileSignature', '')  # To be filled with JWS
    
    def _build_master_files(self, customers: List[Dict], products: List[Dict]) -> None:
        """Build MasterFiles section"""
        
        master_files = SubElement(self.root, 'MasterFiles')
        
        # Customers section
        customers_elem = SubElement(master_files, 'Customers')
        self._add_element(customers_elem, 'NumberOfCustomers', str(len(customers)))
        
        for customer in customers:
            self._add_customer(customers_elem, customer)
        
        # Products section
        products_elem = SubElement(master_files, 'Products')
        self._add_element(products_elem, 'NumberOfProducts', str(len(products)))
        
        for product in products:
            self._add_product(products_elem, product)
    
    def _add_customer(self, parent: Element, customer: Dict[str, Any]) -> None:
        """Add individual customer to MasterFiles"""
        
        customer_elem = SubElement(parent, 'Customer')
        
        # NIF (mandatory for AGT)
        self._add_element(customer_elem, 'RegistrationNumber', customer.get('nif', ''))
        self._add_element(customer_elem, 'Name', customer.get('name', ''))
        
        # Address
        address = SubElement(customer_elem, 'Address')
        self._add_element(address, 'AddressDetail', customer.get('address_detail', ''))
        self._add_element(address, 'City', customer.get('city', ''))
        self._add_element(address, 'PostalCode', customer.get('postal_code', ''))
        self._add_element(address, 'Country', customer.get('country', 'AO'))
        
        # Contact
        self._add_element(customer_elem, 'Telephone', customer.get('telephone', ''))
        self._add_element(customer_elem, 'Email', customer.get('email', ''))
        
        # Self-billing indicator
        self._add_element(customer_elem, 'SelfBillingIndicator', '0')  # 0=No, 1=Yes
    
    def _add_product(self, parent: Element, product: Dict[str, Any]) -> None:
        """Add individual product to MasterFiles"""
        
        product_elem = SubElement(parent, 'Product')
        
        # Product identification
        self._add_element(product_elem, 'ProductCode', product.get('product_code', ''))
        self._add_element(product_elem, 'ProductDescription', product.get('description', ''))
        self._add_element(product_elem, 'ProductType', product.get('product_type', '01'))
        
        # Unit price
        unit_price_elem = SubElement(product_elem, 'UnitPrice')
        self._add_element(unit_price_elem, 'Value', str(Decimal(str(product.get('unit_price', 0)))))
        self._add_element(unit_price_elem, 'CurrencyCode', product.get('currency', 'AOA'))
        
        # Tax information
        tax_info = SubElement(product_elem, 'TaxInformation')
        self._add_element(tax_info, 'TaxType', 'IVA')
        self._add_element(tax_info, 'TaxCountryRegion', 'AO')
        
        # IVA details (mandatory)
        iva_elem = SubElement(tax_info, 'IVA')
        self._add_element(iva_elem, 'IVAType', self._get_iva_type(product.get('iva_regime')))
        
        iva_rate_elem = SubElement(iva_elem, 'IVARate')
        self._add_element(iva_rate_elem, 'Value', str(Decimal(str(product.get('iva_rate', 0)))))
        
        # Exemption code if applicable
        if product.get('iva_exemption_code'):
            self._add_element(iva_elem, 'IVAExemptionCode', product.get('iva_exemption_code'))
    
    def _build_source_documents(
        self,
        invoices: List[Dict],
        credit_notes: List[Dict] = None,
        debit_notes: List[Dict] = None
    ) -> None:
        """Build SourceDocuments section"""
        
        source_docs = SubElement(self.root, 'SourceDocuments')
        
        # Sales Invoices
        if invoices:
            sales_invoices = SubElement(source_docs, 'SalesInvoices')
            self._add_element(sales_invoices, 'NumberOfEntries', str(len(invoices)))
            
            total_debit = Decimal('0')
            for invoice in invoices:
                self._add_invoice(sales_invoices, invoice)
                total_debit += Decimal(str(invoice.get('net_total', 0)))
            
            self._add_element(sales_invoices, 'TotalDebitAmount', str(total_debit))
        
        # Credit Notes
        if credit_notes:
            credit_notes_elem = SubElement(source_docs, 'CreditNotes')
            self._add_element(credit_notes_elem, 'NumberOfEntries', str(len(credit_notes)))
            
            total_credit = Decimal('0')
            for credit in credit_notes:
                self._add_invoice(credit_notes_elem, credit, 'CreditNote')
                total_credit += abs(Decimal(str(credit.get('net_total', 0))))
            
            self._add_element(credit_notes_elem, 'TotalCreditAmount', str(total_credit))
        
        # Debit Notes
        if debit_notes:
            debit_notes_elem = SubElement(source_docs, 'DebitNotes')
            self._add_element(debit_notes_elem, 'NumberOfEntries', str(len(debit_notes)))
            
            total_debit = Decimal('0')
            for debit in debit_notes:
                self._add_invoice(debit_notes_elem, debit, 'DebitNote')
                total_debit += Decimal(str(debit.get('net_total', 0)))
            
            self._add_element(debit_notes_elem, 'TotalDebitAmount', str(total_debit))
    
    def _add_invoice(
        self,
        parent: Element,
        invoice: Dict[str, Any],
        doc_type: str = 'Invoice'
    ) -> None:
        """Add individual invoice/note to SourceDocuments"""
        
        doc_elem = SubElement(parent, 'Sales' if doc_type == 'Invoice' else doc_type)
        
        # Invoice header
        self._add_element(doc_elem, 'InvoiceNumber', invoice.get('invoice_number', ''))
        self._add_element(doc_elem, 'InvoiceDate', invoice.get('invoice_date', '').split('T')[0])
        
        # Party information
        billing_party = SubElement(doc_elem, 'BillingParty')
        self._add_element(billing_party, 'RegistrationNumber', invoice.get('supplier_nif', ''))
        self._add_element(billing_party, 'Name', invoice.get('supplier_name', ''))
        
        billed_party = SubElement(doc_elem, 'BilledParty')
        self._add_element(billed_party, 'RegistrationNumber', invoice.get('customer_nif', ''))
        self._add_element(billed_party, 'Name', invoice.get('customer_name', ''))
        
        # Line items
        lines_elem = SubElement(doc_elem, 'Lines')
        for line in invoice.get('lines', []):
            self._add_invoice_line(lines_elem, line)
        
        # Totals
        document_totals = SubElement(doc_elem, 'DocumentTotals')
        self._add_element(document_totals, 'TaxPayableAmount', 
                        str(invoice.get('iva_total', 0)))
        self._add_element(document_totals, 'NetTotal', 
                        str(invoice.get('net_total', 0)))
        self._add_element(document_totals, 'GrossTotal', 
                        str(invoice.get('gross_total', 0)))
        
        # Signature (if available)
        if invoice.get('signature_jws'):
            self._add_element(doc_elem, 'DocumentSignature', invoice.get('signature_jws'))
        
        # Status
        self._add_element(doc_elem, 'DocumentStatus', 
                        self._get_document_status(invoice.get('status')))
    
    def _add_invoice_line(self, parent: Element, line: Dict[str, Any]) -> None:
        """Add invoice line item"""
        
        line_elem = SubElement(parent, 'Line')
        
        # Line number and description
        self._add_element(line_elem, 'LineNumber', str(line.get('line_number', '')))
        self._add_element(line_elem, 'Description', line.get('description', ''))
        
        # Quantity and Unit Price
        self._add_element(line_elem, 'Quantity', str(line.get('quantity', 0)))
        
        unit_price = SubElement(line_elem, 'UnitPrice')
        self._add_element(unit_price, 'Value', str(line.get('unit_price', 0)))
        
        # Line totals
        self._add_element(line_elem, 'LineGross', str(line.get('line_gross', 0)))
        
        # Tax information
        tax = SubElement(line_elem, 'Tax')
        self._add_element(tax, 'TaxType', 'IVA')
        self._add_element(tax, 'TaxCountryRegion', 'AO')
        
        iva = SubElement(tax, 'IVA')
        self._add_element(iva, 'IVAType', self._get_iva_type(line.get('iva_regime')))
        
        iva_rate = SubElement(iva, 'IVARate')
        self._add_element(iva_rate, 'Value', str(line.get('iva_rate', 0)))
        
        self._add_element(iva, 'IVATaxableAmount', str(line.get('line_gross', 0)))
        self._add_element(iva, 'IVATaxAmount', str(line.get('iva_amount', 0)))
        
        if line.get('iva_exemption_code'):
            self._add_element(iva, 'IVAExemptionCode', line.get('iva_exemption_code'))
        
        self._add_element(line_elem, 'LineNet', str(line.get('line_net', 0)))
    
    @staticmethod
    def _get_iva_type(regime: str) -> str:
        """Convert IVA regime to SAF-T type"""
        regime_map = {
            'GENERAL': 'Normal',
            'SIMPLIFIED': 'Simplified',
            'EXEMPT': 'Exempted',
            'NOT_SUBJECT': 'NotSubject',
            'REVERSE_CHARGE': 'ReverseCharge',
        }
        return regime_map.get(regime, 'Normal')
    
    @staticmethod
    def _get_document_status(status: str) -> str:
        """Convert document status to SAF-T status"""
        status_map = {
            'D': 'Normal',
            'I': 'Normal',
            'C': 'Cancelled',
            'S': 'Pending',
            'A': 'Normal',
            'R': 'Invalid',
            'T': 'Normal',  # Rectified
        }
        return status_map.get(status, 'Normal')
    
    @staticmethod
    def _add_element(parent: Element, tag: str, text: str) -> None:
        """Add simple text element"""
        elem = SubElement(parent, tag)
        elem.text = str(text) if text else ''
    
    def _format_xml(self) -> str:
        """Format XML with proper indentation"""
        rough_string = tostring(self.root, encoding='unicode')
        reparsed = minidom.parseString(rough_string)
        return reparsed.toprettyxml(indent="  ")


class SAFTAOValidator:
    """Validate SAF-T (AO) XML against AGT rules"""
    
    @staticmethod
    def validate_structure(root: Element) -> Tuple[bool, str]:
        """Validate basic XML structure"""
        if root.tag != 'AuditFile':
            return False, "Root element must be 'AuditFile'"
        
        required_sections = ['Header', 'MasterFiles', 'SourceDocuments']
        for section in required_sections:
            if root.find(section) is None:
                return False, f"Missing required section: {section}"
        
        return True, ""
    
    @staticmethod
    def validate_header(header: Element) -> Tuple[bool, str]:
        """Validate Header section against AGT requirements"""
        required_fields = ['AuditFileVersion', 'AuditFileCountry', 'Company']
        for field in required_fields:
            if header.find(field) is None:
                return False, f"Missing required header field: {field}"
        
        country = header.findtext('AuditFileCountry', '')
        if country != 'AO':
            return False, f"AuditFileCountry must be 'AO', got '{country}'"
        
        return True, ""


from typing import Tuple

__all__ = [
    'SAFTAOGenerator',
    'SAFTAOValidator',
]
