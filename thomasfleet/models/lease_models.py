# -*- coding: utf-8 -*-

from odoo import models, fields, api
from datetime import date, datetime, timedelta
from dateutil import relativedelta

class ThomasLease(models.Model):

    def _getLeaseDefault(self):
        return self.env['thomasfleet.lease_status'].search([('name', '=', 'Draft')], limit=1).id

    _name = 'thomaslease.lease'
    lease_number = fields.Char('Lease ID',readonly=True)
    po_number = fields.Char("Purchase Order #")
    po_comments= fields.Char("Purchase Order Comments")
    contract_number = fields.Char("Contract #")
    lease_status = fields.Many2one('thomasfleet.lease_status', string='Lease Status', default=_getLeaseDefault)
    lease_start_date = fields.Date("Rental Period is from")
    lease_return_date = fields.Date("Rental Returned on")
    billing_notes = fields.Char("Billing Notes")
    min_lease_end_date = fields.Date("To")
    monthly_rate = fields.Float("Monthly Rate")
    weekly_rate=fields.Float("Weekly Rate")
    daily_rate=fields.Float("Daily Rate")
    monthly_mileage = fields.Integer("Monthly Mileage")
    mileage_overage_rate =fields.Float("Additional Mileage Charge")
    customer_id = fields.Many2one("res.partner", "Customer")
    #contact_ap_id =fields.Many2one("res.partner", "Invoicing Contact", domain="[('parent_id','=',customer_id)]")
    #contact_driver_id = fields.Many2one("res.partner", "Driver", domain="[('parent_id','=',customer_id)]")
    vehicle_id = fields.Many2one("fleet.vehicle", string="Unit #")
    #contact_three=fields.Many2one("res.partner", "Contact #3", domain="[('parent_id','=',customer_id)]")
    #contact_four=fields.Many2one("res.partner", "Contact #4", domain="[('parent_id','=',customer_id)]")
    #contact_five=fields.Many2one("res.partner", "Contact #5", domain="[('parent_id','=',customer_id)]")

    ap_contact_ids = fields.Many2many('res.partner',string='Accounts Payable Contacts',
                                      relation='lease_agreement_res_partner_ap_rel',
                                      domain="[('parent_id','=',customer_id)]")
    po_contact_ids = fields.Many2many('res.partner', string='Purchasing Contacts',
                                      relation='lease_agreement_res_partner_po_rel',
                                      domain="[('parent_id','=',customer_id)]")
    ops_contact_ids = fields.Many2many('res.partner', string='Operations Contacts',
                                       relation='lease_agreement_res_partner_ops_rel',
                                       domain="[('parent_id','=',customer_id)]")

    #unit_no = fields.Many2one("fleet.vehicle.unit_no", "Unit No")
    unit_no = fields.Char('Unit #',related="vehicle_id.unit_no",readonly=True)
    inclusions = fields.Many2many(related="vehicle_id.inclusions", string="Inclusions", readonly=True)
    accessories = fields.One2many(related="vehicle_id.accessories", string="Accessories", readonly=True)
   # inclusions_base_rate = fields.Float(compute="_calcBaseIncRate", string="Inclusion List Rate")
    inclusions_discount = fields.Float('Inclusion Discount')
    lease_notes=fields.Char("Lease Notes")
    additional_billing = fields.Char("Additional Billing")
    payment_method = fields.Char("Payment Method")

    #inclusion_rate= fields.float(compute="_calIncRate",string='Inclusion Rate')
    #accessories_base_rate = fields.Float(compute="_calcBaseAccRate", string="Accessor List Rate")
   # accessory_discount=fields.float('Accessor Discount')
    #accessory_rate =fields.float(compute="_caclAccRate",string='Accessory Rate')


    @api.multi
    def write(self, values):
        ThomasLease_write = super(ThomasLease, self).write(values)

        if not ThomasLease.lease_number:
            Agreements = self.env['thomaslease.lease']
            aCount = 0
            if ThomasLease.customer_id:
                aCount = Agreements.search_count([('customer_id', '=', ThomasLease.customer_id.id)])
                ThomasLease.lease_number = str(ThomasLease.customer_id.name) + "_" + str(ThomasLease.unit_no) + "_" + str(
                    ThomasLease.lease_start_date) + "_" + str(aCount)

        # ThomasFleetVehicle_write.get_protractor_id()
        return ThomasLease_write

    @api.multi
    @api.depends('lease_number')
    def name_get(self):
        res = []
        for record in self:
            name = record.lease_number
            res.append((record.id, name))
        return res


    @api.model
    def create(self, data):
        record = super(ThomasLease, self).create(data)
        Agreements = self.env['thomaslease.lease']
        aCount = 0
        if record.customer_id:
            aCount = Agreements.search_count([('customer_id', '=', record.customer_id.id)])

        record.lease_number = str(record.customer_id.name)+"_"+str(record.unit_no)+"_"+str(record.lease_start_date)+"_"+str(aCount)

        return record

class ThomasFleetLeaseInvoiceWizard(models.TransientModel):

    def _default_lease_ids(self):
        #for the_id in self.env.context.get('active_ids'):
        #    print(the_id.name)
        return self.env.context.get('active_ids')

    def _default_invoice_date(self):
        return datetime.now()

    def _default_invoice_due_date(self):
        dt2 = datetime.now() + relativedelta.relativedelta(months=+1)
        return dt2

    _name = 'thomaslease.lease.invoice.wizard'
    lease_ids = fields.Many2many('thomaslease.lease', string="Lease", default=_default_lease_ids)
    invoice_date = fields.Date(string="Invoice Date", default=_default_invoice_date)
    invoice_due_date = fields.Date(string="Invoice Due Date", default=_default_invoice_due_date)

    @api.multi
    def record_lease_invoices(self):
        accounting_invoice = self.env['account.invoice']
        for wizard in self:
            print("WIZARD")
            leases = wizard.lease_ids
            for lease in leases:
                # determine if an invoice already exists for the lease and don't create again...warn user
                aLease = self.env['thomaslease.lease'].browse(lease)

                print("Accounting Invoice Create " + str(wizard.invoice_date) + " : " + str(aLease.id))
                product = self.env['product.product'].search([('name', '=', 'Lease')])


                line = self.env['account.invoice.line']
                line_ids=[]
                line_id ={
                    'product_id': product.id,
                    'price_unit': aLease.id.monthly_rate,
                    'quantity': 1,
                    'name': 'Monthly Lease for Unit # ' + aLease.id.vehicle_id.unit_no,
                    'account_id': product.property_account_income_id.id
                }
                line_ids.append((0,0,line_id))
                accounting_invoice.create({
                    'partner_id':aLease.id.customer_id.id,
                    'vechicle_id': aLease.id.vehicle_id.id,
                    'date_invoice': wizard.invoice_date,
                    'date_due' : wizard.invoice_due_date,
                    'type': 'out_invoice',
                    'invoice_line_ids': line_ids
                })
                # accounting_invoice.create({}) need to match customer to accounting invoice etc
'''
    @api.depends('customer_id', 'unit_no','lease_start_date')
    def _calcLeaseNumber(self):
        Agreements = self.env['thomaslease.lease']
        aCount = 0
        for record in self:
            if record.customer_id:
                aCount = Agreements.search_count([('customer_id', '=', record.customer_id.id)])

            record.lease_number = str(record.customer_id.name)+"_"+str(record.unit_no)+"_"+str(record.lease_start_date)+"_"+str(aCount+1)
'''
'''
    @api.depends('inclusions')
    def __calcBaseIncRate(self):

        Agreements = self.env['thomasfleet.inclusion']
        for record in self:
            res = Agreements.search([('vehicle_id', '=', record.id)])
            for inc in res:
                record.inclusions
'''
