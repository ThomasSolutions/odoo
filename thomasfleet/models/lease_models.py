# -*- coding: utf-8 -*-

from odoo import models, fields, api
from datetime import date, datetime, timedelta
from dateutil import relativedelta
import calendar
import math


class ThomasLease(models.Model):
    _inherit = 'mail.thread'

    def _getLeaseDefault(self):
        return self.env['thomasfleet.lease_status'].search([('name', '=', 'Draft')], limit=1).id

    def _get_rate_type(self):
        for rec in self:
            rate_str = ''
            for lines in rec.lease_lines:
                if lines.product_id.rate_type:
                    if rate_str == '':
                        rate_str += str(lines.product_id.rate_type)
                    else:
                        rate_str += ', '+str(lines.product_id.rate_type)
                else:
                    rate_str = 'NO SET'
            rec.rate_type = rate_str

    def _search_rate_type(self,operator,value):
        lease_ids = []
        records = self.env['thomaslease.lease'].search([])
        for rec in records:
            for lines in rec.lease_lines:
                if 'not' in operator or '!' in operator:
                    if not lines.product_id.rate_type:
                        lease_ids.append(rec.id)
                    if lines.product_id.rate_type != value:
                        lease_ids.append(rec.id)
                else:
                    if lines.product_id.rate_type == value:
                        lease_ids.append(rec.id)

        return [('id', 'in', lease_ids)]

    @api.onchange('vehicle_id')
    def _get_unit_odometer(self):
        self.mileage_at_lease = self.vehicle_id.odometer

    @api.constrains('vehicle_id')
    def check_vehicle_is_available(self):
        for rec in self:
            for lease_agreement in rec.vehicle_id.lease_agreements:
                if lease_agreement.state == 'active':
                    raise models.ValidationError(
                        'Unit: ' + rec.vehicle_id.unit_no +
                        ' is currently associated with an Active lease agreement: ' + lease_agreement.lease_number)

                if lease_agreement.state == 'repairs_pending':
                    raise models.ValidationError(
                        'Unit: ' + rec.vehicle_id.unit_no +
                        ' is currently associated with an Repairs Pending lease agreement: ' + lease_agreement.lease_number)

    @api.depends('customer_id')
    @api.one
    def _set_preferred_billing_default(self):
        return self.env['res.partner'].search([('id', '=', self.customer_id)]).preferred_payment

    @api.onchange("lease_start_date")
    def set_billing_start_date(self):
        print("Setting Billing Start Date")
        if not self.billing_start_date:
            self.billing_start_date = self.lease_start_date

    @api.onchange("lease_start_date")
    def set_invoice_dates(self):
        if self.lease_start_date:
            if not self.billing_start_date:
                self.billing_start_date = self.lease_start_date

            lease_start_date = datetime.strptime(self.billing_start_date, '%Y-%m-%d')

            today = date.today()
            last_day_lease_month = calendar.monthrange(lease_start_date.year, lease_start_date.month)[1]
            start_of_current_month = date(today.year, today.month, 1)
            start_of_next_month = date(lease_start_date.year, lease_start_date.month + 1, 1)
            tmp_invoice_to = None

            if (lease_start_date.month == today.month) and (lease_start_date.year == today.year):
                if not self.invoice_ids:
                    self.run_initial_invoicing = True
                    self.invoice_posting_date = date(today.year, today.month, last_day_lease_month)
                    self.invoice_from = lease_start_date
                    tmp_invoice_to = date(today.year, today.month, last_day_lease_month)
            else:
                self.run_initial_invoicing = False
                self.invoice_posting_date = date(today.year, today.month, 1)
                self.invoice_from = date(today.year, today.month, 1)
                tmp_invoice_to = date(today.year, today.month, last_day_lease_month)

            self.invoice_generation_date = date.today()

            if self.lease_return_date:
                self.invoice_to = self.lease_return_date
                self.requires_manual_calculations = True
            else:
                self.invoice_to = tmp_invoice_to

    @api.onchange("customer_id")
    def set_preferred_payment(self):
        print("Setting Payment Start Date")
        # self.preferred_payment = self.env['res.partner'].search([('id', '=', self.customer_id)]).preferred_payment

    @api.multi
    def btn_validate(self):
        for rec in self:
            rec.state = 'active'

    @api.multi
    def lease_print(self):
        """ Print the invoice and mark it as sent, so that we can see more
            easily the next step of the workflow
        """
        self.ensure_one()
        return self.env.ref('thomasfleet.lease_agreement').report_action(self)

    _name = 'thomaslease.lease'
    lease_number = fields.Char('Lease ID')
    po_number = fields.Char("Purchase Order #")
    po_comments = fields.Char("Purchase Order Comments")
    contract_number = fields.Char("Contract #")
    invoice_ids = fields.Many2many('account.invoice', string='Invoices',
                                   relation='lease_agreement_account_invoice_rel')
    # lease_status = fields.Many2one('thomasfleet.lease_status', string='Lease Status', default=_getLeaseDefault)
    state = fields.Selection([('draft', 'Draft'), ('active', 'Active'),
                              ('repairs_pending', 'Repairs Pending'),
                              ('invoice_pending', 'Invoice Pending'),
                              ('both', 'Repairs and Invoice Pending'),
                              ('closed', 'Closed')], string="Status", default='draft')

    lease_start_date = fields.Date("Lease Start Date", required=True)

    billing_start_date = fields.Date("Billing Start Date")

    invoice_from = fields.Date(string="Invoice From")
    invoice_to = fields.Date(string="Invoice To")
    invoice_posting_date = fields.Date(string="Invoice Posting Date")
    invoice_generation_date = fields.Date(string="Invoice Generation Date")
    run_initial_invoicing = fields.Boolean(string="Initial Invoice", default=False)
    preferred_payment = fields.Selection([('credit card', 'Credit Card'), ('pad1', 'PAD with Invoice Sent'),
                                          ('pad2', 'PAD no Invoice Sent'), ('customer', 'Customer')],
                                         )
    lease_return_date = fields.Date("Unit Returned on")
    requires_manual_calculations = fields.Boolean("Requires Manual Calculations", default=False)
    billing_notes = fields.Char("Billing Notes")
    min_lease_end_date = fields.Date("To")
    fuel_at_lease = fields.Selection([('one_quarter', '1/4'), ('half', '1/2'),
                                      ('three_quarter', '3/4'), ('full', 'Full')],
                                     )
    fuel_at_return = fields.Selection([('one_quarter', '1/4'), ('half', '1/2'),
                                       ('three_quarter', '3/4'), ('full', 'Full')],
                                      )

    lease_out_odometer_id = fields.Many2one('fleet.vehicle.odometer', string="Odometer at Lease",
                                            domain="[('vehicle_id','=',vehicle_id), ('activity','=','lease_out')]")
    lease_return_odometer_id = fields.Many2one('fleet.vehicle.odometer', string="Odometer at Return",
                                               domain="[('vehicle_id','=',vehicle_id), ('activity','=','lease_in')]")
    mileage_at_lease = fields.Float(string='Lease Start Odometer', related='lease_out_odometer_id.value', readonly=True)

    mileage_at_return = fields.Float(string='Lease Return Odometer', related='lease_return_odometer_id.value',
                                     readonly=True)

    delivery_charge = fields.Float(string='Delivery Charge')

    driver_id = fields.Many2one('res.partner', string='Driver', domain="[('parent_id','=',customer_id)]")

    monthly_rate = fields.Float("Monthly Rate")
    weekly_rate = fields.Float("Weekly Rate")
    daily_rate = fields.Float("Daily Rate")
    monthly_tax = fields.Float("Tax(HST-13%)")
    monthly_total = fields.Float("Monthly Lease Total")
    monthly_mileage = fields.Integer("Monthly Mileage Allowance", default=3500)
    mileage_overage_rate = fields.Float("Additional Mileage Rate", default=0.14)

    customer_id = fields.Many2one("res.partner", "Customer", change_default=True, required=True)

    vehicle_id = fields.Many2one("fleet.vehicle", string="Unit #", change_default=True, required=True)

    unit_slug = fields.Char("Unit", related="vehicle_id.unit_slug", readonly=True)
    lease_lines = fields.One2many('thomaslease.lease_line', 'lease_id', string='Lease Lines', change_default = True, copy=True, auto_join=True)
    # product_ids = fields.Many2many("product.product",relation='lease_agreeement_product_product_rel', string="Products")

    insurance_on_file = fields.Boolean(related='customer_id.insurance_on_file', string="Proof of Insurance on File",
                                       readonly=True)
    insurance_agent = fields.Char(related='customer_id.insurance_agent', string="Agent", readonly=True)
    insurance_underwriter = fields.Char(related='customer_id.insurance_underwriter', string="Underwriter",
                                        readonly=True)
    insurance_policy = fields.Char(related='customer_id.insurance_policy', string="Policy #", readonly=True)
    insurance_expiration = fields.Date(related='customer_id.insurance_expiration', string="Expiration Date",
                                       readonly=True)

    ap_contact_ids = fields.Many2many('res.partner', string='Accounts Payable Contacts',
                                      relation='lease_agreement_res_partner_ap_rel',
                                      domain="[('parent_id','=',customer_id)]")
    po_contact_ids = fields.Many2many('res.partner', string='Purchasing Contacts',
                                      relation='lease_agreement_res_partner_po_rel',
                                      domain="[('parent_id','=',customer_id)]")
    ops_contact_ids = fields.Many2many('res.partner', string='Operations Contacts',
                                       relation='lease_agreement_res_partner_ops_rel',
                                       domain="[('parent_id','=',customer_id)]")

    # unit_no = fields.Many2one("fleet.vehicle.unit_no", "Unit No")
    unit_no = fields.Char('Unit #', related="vehicle_id.unit_no", readonly=True)
    rate_type = fields.Char("Rate Type", compute='_get_rate_type', search='_search_rate_type')
    inclusions = fields.Many2many(related="vehicle_id.inclusions", string="Inclusions", readonly=True)
    accessories = fields.One2many(related="vehicle_id.accessories", string="Accessories", readonly=True)
    # inclusions_base_rate = fields.Float(compute="_calcBaseIncRate", string="Inclusion List Rate")
    inclusions_discount = fields.Float('Inclusion Discount')
    lease_notes = fields.Text("Lease Notes")
    inspection_notes = fields.Text("Inspection Notes")
    additional_billing = fields.Char("Additional Billing")
    payment_method = fields.Char("Payment Method")
    last_invoice_date = fields.Date("Last Invoice On")
    additional_charges = fields.Boolean("Additional Charges")
    outgoing_inspector = fields.Many2one('res.users', string="Outgoing Inspector")
    incoming_inspector = fields.Many2one('res.users', string="Incoming Inspector")
    transponder_id = fields.Many2one('thomasfleet.accessory', string="407 Transponder",
                                     domain="[('type.name','=','407 Transponder')]")

    aggregation_id = fields.Char("Aggregate ID")

    # last_invoice_age = fields.Integer("Last Invoice Age", compute='calc_invoice_age')

    # inclusion_rate= fields.float(compute="_calIncRate",string='Inclusion Rate')
    # accessories_base_rate = fields.Float(compute="_calcBaseAccRate", string="Accessor List Rate")
    # accessory_discount=fields.float('Accessor Discount')
    # accessory_rate =fields.float(compute="_caclAccRate",string='Accessory Rate')
    @api.depends('last_invoice_date')
    def calc_invoice_age(self):
        for rec in self:
            if rec.last_invoice_date:
                age = datetime.now() - rec.last_invoice_date
                rec.last_invoice_age = age.days
            else:
                rec.last_invoice_age = 0

    @api.onchange('customer_id', 'lease_start_date', 'vehicle_id')
    def update_lease_number(self):
        Agreements = self.env['thomaslease.lease']
        aCount = 0

        if self.state == 'draft':
            if self.customer_id:
                aCount = Agreements.search_count([('customer_id', '=', self.customer_id.id)])

            self.lease_number = str(self.customer_id.name) + "_" + \
                                str(self.vehicle_id.unit_no) + "_" + \
                                str(self.lease_start_date) + "_" + str(aCount)

    @api.onchange("lease_lines")
    def update_totals(self):
        self.monthly_rate = 0
        tax = 0
        for line in self.lease_lines:
            self.monthly_rate = self.monthly_rate + line.price
            tax = tax + line.tax_amount

        self.monthly_tax = tax
        self.monthly_total = self.monthly_rate + self.monthly_tax

    '''
    @api.multi
    @api.depends('customer_id', 'lease_start_date', 'unit_no')
    def write(self, values):
        ThomasLease_write = super(ThomasLease, self).write(values)

        if not ThomasLease.lease_number:
            Agreements = self.env['thomaslease.lease']
            aCount = 0
            if ThomasLease.customer_id:
                aCount = Agreements.search_count([('customer_id', '=', ThomasLease.customer_id.id)])
                ThomasLease.lease_number = str(ThomasLease.customer_id.name) + "_" + str(
                    ThomasLease.unit_no) + "_" + str(
                    ThomasLease.lease_start_date) + "_" + str(aCount)

        # ThomasFleetVehicle_write.get_protractor_id()
        return ThomasLease_write
    '''

    @api.multi
    @api.depends('lease_number')
    def name_get(self):
        res = []
        for record in self:
            name = record.lease_number
            res.append((record.id, name))
        return res

    '''
    @api.model
    def create(self, data):
        record = super(ThomasLease, self).create(data)
        Agreements = self.env['thomaslease.lease']
        aCount = 0
        if record.customer_id:
            aCount = Agreements.search_count([('customer_id', '=', record.customer_id.id)])

        record.lease_number = str(record.customer_id.name) + "_" + str(record.unit_no) + "_" + str(
            record.lease_start_date) + "_" + str(aCount)

        return record
    '''


class ThomasFleetLeaseLine(models.Model):
    _name = 'thomaslease.lease_line'

    @api.depends('product_id')
    def default_description(self):
        return self.product_id.description_sale

    @api.depends('product_id')
    def default_price(self):
        return self.product_id.list_price

    @api.depends('product_id')
    def default_taxes(self):
        return self.product_id.taxes_id

    @api.depends('price', 'tax')
    def default_total(self):
        return self.price * (1 + (float(self.tax) / 100))

    lease_id = fields.Many2one('thomaslease.lease', string='Lease Reference', required=True, ondelete='cascade',
                               index=True, copy=False)
    product_id = fields.Many2one('product.product', string='Product', change_default=True, ondelete='restrict',
                                 required=True)
    description = fields.Char(string="Description", default=default_description)
    tax_id = fields.Many2one('account.tax', string='Tax')
    # fields.Many2many('account.tax', string='Taxes', domain=['|', ('active', '=', False), ('active', '=', True)])
    tax_ids = fields.Many2many('account.tax', string='Taxes',
                               domain=['|', ('active', '=', False), ('active', '=', True)])
    price = fields.Float(string="Price", default=default_price)
    tax = fields.Char(string="Tax Rate %", default="13")
    tax_amount = fields.Float(string="Tax Amount")
    total = fields.Float(string="Total", default=default_total)

    @api.onchange('product_id')
    def update_product(self):
        self.description = self.product_id.description_sale
        self.price = self.product_id.list_price
        self.tax_amount = self.product_id.list_price * (float(self.tax_id.amount) / 100)
        self.total = self.price * (1 + (float(self.tax_id.amount) / 100))
        self.tax_ids = self.product_id.taxes_id
        if self.product_id.taxes_id:
            self.tax_id = self.product_id.taxes_id[0]


    @api.onchange('price', 'tax')
    def update_total(self):
        self.tax_amount = self.price * (float(self.tax_id.amount) / 100)
        self.total = self.price * (1 + (float(self.tax_id.amount) / 100))


class ThomasFleetReturnWizard(models.TransientModel):
    _name = 'thomaslease.lease.return.wizard'

    def _default_lease_ids(self):
        # for the_id in self.env.context.get('active_ids'):
        #    print(the_id.name)
        return self.env.context.get('active_ids')

    lease_ids = fields.Many2many('thomaslease.lease', string="Lease", default=_default_lease_ids)
    invoice_pending = fields.Boolean("Invoice Pending")
    repairs_pending = fields.Boolean("Repairs Pending")

    @api.multi
    def record_return(self):
        for lease in self.lease_ids:
            if self.invoice_pending & self.repairs_pending:
                lease.state = 'both'
            elif self.invoice_pending:
                lease.state = 'invoice_pending'
            elif self.repairs_pending:
                lease.state = 'repairs_pending'
            else:
                lease.state = 'closed'


class ThomasFleetLeaseInvoiceWizard(models.TransientModel):

    def _default_lease_ids(self):
        # for the_id in self.env.context.get('active_ids'):
        #    print(the_id.name)
        return self.env.context.get('active_ids')

    def _default_invoice_date(self):
        return datetime.now()

    def _default_invoice_due_date(self):
        dt2 = datetime.now() + relativedelta.relativedelta(months=+1)
        return dt2

    def pro_rate_monthly_lease(self, monthly_total, start_date, end_date):

        start_d = datetime.strptime(start_date, '%Y-%m-%d')
        end_d = datetime.strptime(end_date, '%Y-%m-%d')
        num_days = (end_d - start_d).days
        daily_rate = (monthly_total * 12.5) / 100
        weekly_rate = (monthly_total * 45) / 100
        days_in_month = calendar.monthrange(end_d.year, end_d.month)[1]
        amount = monthly_total

        if num_days < 7:
            amount = num_days * daily_rate
        elif num_days >= 7 and days_in_month > num_days:
            days = num_days % 7
            weeks = math.floor(num_days / 7)
            amount = (days * daily_rate) + (weeks * weekly_rate)

        return amount

    def calc_amd_rate(self, rate_type, line_amount, start_date, end_date):

        pu_monthly = 663.00
        pu_weekly = 140.00
        pu_daily = 31.90

        cc_monthly = 664.00
        cc_weekly = 200.00
        cc_daily = 35.50

        ts_weekly = 475.00
        ts_daily = 95.00

        tr_weekly = 575.00
        tr_daily = 135.00

        ft_monthly = 2350.00

        start_d = datetime.strptime(start_date, '%Y-%m-%d')
        end_d = datetime.strptime(end_date, '%Y-%m-%d')
        num_days = (end_d - start_d).days
        days_in_month = calendar.monthrange(end_d.year, end_d.month)[1]
        amount = 0
        if rate_type == 'amd_daily_pu':
            if num_days < 7:
                amount = num_days * pu_daily
            elif num_days >= 7 and num_days < days_in_month:
                days = num_days % 7
                weeks = math.floor(num_days / 7)
                the_amt = (days * pu_daily)+ (weeks * pu_weekly)
                if the_amt > pu_monthly:
                    amount = the_amt
                else:
                    amount = pu_monthly

        if rate_type == 'amd_daily_cc':
            if num_days < 7:
                amount = num_days * cc_daily
            elif num_days >= 7 and num_days < days_in_month:
                days = num_days % 7
                weeks = math.floor(num_days / 7)
                the_amt = (days * cc_daily)+ (weeks * cc_weekly)
                if the_amt > cc_monthly:
                    amount = the_amt
                else:
                    amount = cc_monthly

        if rate_type == 'amd_daily_ts':
            if num_days < 7:
                amount = num_days * ts_daily
            elif num_days >= 7 and num_days < days_in_month:
                days = num_days % 7
                weeks = math.floor(num_days / 7)
                amount = (days * ts_daily)+ (weeks * ts_weekly)

        if rate_type == 'amd_daily_tr':
            if num_days < 7:
                amount = num_days * tr_daily
            elif num_days >= 7 and num_days < days_in_month:
                days = num_days % 7
                weeks = math.floor(num_days / 7)
                amount = (days * tr_daily) + (weeks * tr_weekly)

        if rate_type == 'amd_daily_ft':
            amount = (num_days/days_in_month) * ft_monthly

        return amount

    def calc_stelco_rate(self, rate_type, line_amount, start_date, end_date):
        start_d = datetime.strptime(start_date, '%Y-%m-%d')
        end_d = datetime.strptime(end_date, '%Y-%m-%d')
        num_days = (end_d - start_d).days
        days_in_month = calendar.monthrange(end_d.year, end_d.month)[1]

        amount = 0
        if rate_type == 'stelco_daily':
            amount = num_days * line_amount
        elif rate_type == 'stelco_monthly':
            daily_rate = (line_amount * 12.5) / 100
            weekly_rate = (line_amount * 45) / 100

            if num_days < 7:
                amount = num_days * daily_rate
            elif num_days >= 7 and num_days < days_in_month:
                days = num_days % 7
                weeks = math.floor(num_days / 7)
                amount = (days * daily_rate) + (weeks * weekly_rate)


        return amount

    def calculate_line_amount(self, product, line_amount, start_date, end_date):

        print("CALC AMOUNT FOR : " + product.categ_id.name)
        the_amount = line_amount
        if product.rate_type == 'monthly':
            the_amount = self.pro_rate_monthly_lease(line_amount, start_date, end_date)
        elif product.rate_type == 'weekly':
            the_amount = self.pro_rate_monthly_lease(line_amount, start_date, end_date)
        elif product.rate_type == 'daily':
            the_amount = self.pro_rate_monthly_lease(line_amount, start_date, end_date)
        elif 'amd' in product.rate_type:
            the_amount = self.calc_amd_rate(product.rate_type, line_amount, start_date, end_date)
        elif 'stelco' in product.rate_type:
            the_amount = self.calc_stelco_rate(product.rate_type, line_amount, start_date, end_date)

        return the_amount
        '''
        start_d = datetime.strptime(start_date, '%Y-%m-%d')
        end_d = datetime.strptime(end_date, '%Y-%m-%d')
        num_days = (end_d - start_d).days
        amount = monthly_total

        
        if num_days < 7:
            amount = num_days * daily_rate
        elif num_days >= 7 and 21 >= num_days:
            amount = (num_days / 7) * weekly_rate
        elif num_days > 22 and 30 > num_days:
            amount = (num_days /30) * monthy_rate
        '''

    _name = 'thomaslease.lease.invoice.wizard'
    lease_ids = fields.Many2many('thomaslease.lease', string="Lease", default=_default_lease_ids)
    invoice_date = fields.Date(string="Invoice Date", default=_default_invoice_date)
    invoice_due_date = fields.Date(string="Invoice Due Date", default=_default_invoice_due_date)

    def aggregate_lease_selected(self, a_lease):
        resp = False
        for lease in self.lease_ids:
            if a_lease.id == lease.id:
                resp = True
        return resp

    @api.multi
    def record_normal_invoice(self, the_lease, the_wizard):
        accounting_invoice = self.env['account.invoice']

        if the_lease.id.last_invoice_date:
            last = datetime.strptime(the_lease.id.last_invoice_date, '%Y-%m-%d')
            current = datetime.strptime(the_wizard.invoice_due_date, '%Y-%m-%d')
            duration = (current - last).days
            if duration <= 28:
                raise models.UserError(
                    'An invoice for within 30 days already exists for lease agreement ' +
                    the_lease.id.lease_number)

        month = datetime.strptime(the_wizard.invoice_date, '%Y-%m-%d').strftime('%b')
        year = datetime.strptime(the_wizard.invoice_date, '%Y-%m-%d').strftime('%Y')

        if the_lease.id.run_initial_invoicing:
            if the_lease.id.invoice_posting_date:
                last_posting_date = datetime.strptime(the_lease.id.invoice_posting_date, '%Y-%m-%d')
            else:
                last_posting_date = datetime.strptime(the_lease.id.billing_start_date, '%Y-%m-%d')

            if the_lease.id.invoice_from:
                initial_invoice_from = the_lease.id.invoice_from
            else:
                initial_invoice_from = the_lease.id.billing_start_date

            if the_lease.id.invoice_to:
                initial_to = the_lease.id.invoice_to
            else:
                initial_start = datetime.strptime(the_lease.id.billing_start_date, '%Y-%m-%d')
                initial_to = date(initial_start.year, initial_start.month,
                                  calendar.monthrange(initial_start.year, initial_start.month)[1])
                initial_invoice_to = initial_to.strftime('%Y-%m-%d')

            relative_next_month = last_posting_date + relativedelta.relativedelta(months=+1)
            next_posting_date = date(relative_next_month.year, relative_next_month.month, 1)
            next_month_to = calendar.monthrange(next_posting_date.year, next_posting_date.month)[1]
            next_month = next_posting_date.strftime('%b')
            next_year = next_posting_date.strftime('%Y')

        line_ids = []
        next_month_line_ids = []
        lease_invoices = the_lease.id.invoice_ids.ids
        unit_invoices = the_lease.id.vehicle_id.lease_invoice_ids.ids

        for line in the_lease.id.lease_lines:
            product = line.product_id
            invoice_line = self.env['account.invoice.line']
            line_amount = self.calculate_line_amount(product, line.price, initial_invoice_from,
                                                     initial_invoice_to)

            if not the_lease.id.invoice_from:
                due_date = datetime.strptime(the_wizard.invoice_due_date, '%Y-%m-%d').date()
                start_date = date(due_date.year, due_date.month, 1)
            else:
                start_date = datetime.strptime(the_lease.id.invoice_from, '%Y-%m-%d').date()

            if not the_lease.id.invoice_to:
                end_date = datetime.strptime(the_wizard.invoice_due_date, '%Y-%m-%d').date()
            else:
                end_date = datetime.strptime(the_lease.id.invoice_to, '%Y-%m-%d').date()

            num_days = (end_date - start_date).days
            pro_rated = ''
            if line_amount < line.total:
                pro_rated = 'Pro Rated for ' + str(num_days) + ' days '
            # create the invoice line

            line_id = invoice_line.create({
                'product_id': product.id,
                'price_unit': line_amount,
                'quantity': 1,
                'name': pro_rated + month + ' ' + year + ' - Monthly Lease: for Unit # ' + the_lease.id.vehicle_id.unit_no,
                'invoice_line_tax_ids': line.tax_ids,
                'account_id': product.property_account_income_id.id
            })

            # call set taxes to set them...otherwise the relationships aren't set properly
            line_id._set_taxes()
            line_id.price_unit = line_amount
            line_ids.append(line_id.id)

        # TODO: move this out of the line for loop since I think it would create multiple invoice per lease line
        a_invoice = accounting_invoice.create({
            'partner_id': the_lease.id.customer_id.id,
            'vehicle_id': the_lease.id.vehicle_id.id,
            'date_invoice': the_wizard.invoice_date,
            'date_due': the_wizard.invoice_due_date,
            'invoice_from': the_lease.id.invoice_from,
            'invoice_to': the_lease.id.invoice_to,
            'invoice_posting_date': the_lease.id.invoice_posting_date,
            'invoice_generation_date': the_lease.id.invoice_generation_date,
            'type': 'out_invoice',
            'state': 'draft',
            'po_number': the_lease.id.po_number,
            'requires_manual_calculations': the_lease.id.requires_manual_calculations,
            'invoice_line_ids': [(6, 0, line_ids)]
        })
        lease_invoices.append(a_invoice.id)
        unit_invoices.append(a_invoice.id)
        if the_lease.id.run_initial_invoicing:
            for next_line in the_lease.id.lease_lines:
                next_line_amount = self.calculate_line_amount(product, next_line.price,
                                                              next_posting_date.strftime('%Y-%m-%d'),
                                                              relative_next_month.strftime('%Y-%m-%d'))
                pro_rated = ''
                if next_line_amount < next_line.price:
                    pro_rated = 'Pro Rated '

                next_month_line_id = invoice_line.create({
                    'product_id': product.id,
                    'price_unit': next_line_amount,
                    'quantity': 1,
                    'name': pro_rated + next_month + ' ' + next_year + ' - Monthly Lease: for Unit # ' + the_lease.id.vehicle_id.unit_no,
                    'invoice_line_tax_ids': next_line.tax_ids,
                    'account_id': product.property_account_income_id.id
                })

                next_month_line_id._set_taxes()
                next_month_line_id.price_unit = next_line_amount

                next_month_line_ids.append(next_month_line_id.id)

            a_next_invoice = accounting_invoice.create({
                'partner_id': the_lease.id.customer_id.id,
                'vehicle_id': the_lease.id.vehicle_id.id,
                'date_invoice': next_posting_date,
                'date_due': relative_next_month,
                'invoice_from': next_posting_date,
                'invoice_to': relative_next_month,
                'invoice_posting_date': next_posting_date,
                'invoice_generation_date': the_lease.id.invoice_generation_date,
                'type': 'out_invoice',
                'state': 'draft',
                'po_number': the_lease.id.po_number,
                'requires_manual_calculations': the_lease.id.requires_manual_calculations,
                'invoice_line_ids': [(6, 0, next_month_line_ids)]
            })

            lease_invoices.append(a_next_invoice.id)
            unit_invoices.append(a_next_invoice.id)

        the_lease.id.invoice_ids = [(6, 0, lease_invoices)]
        the_lease.id.vehicle_id.lease_invoice_ids = [(6, 0, unit_invoices)]
        the_lease.id.run_initial_invoicing = False

    @api.multi
    def record_aggregate_invoice(self, customers, the_wizard):
        for customer in customers:
            accounting_invoice = self.env['account.invoice']
            po_numbers = []
            ap_groups = []
            aggregation_ids = []

            month = datetime.strptime(the_wizard.invoice_date, '%Y-%m-%d').strftime('%b')
            year = datetime.strptime(the_wizard.invoice_date, '%Y-%m-%d').strftime('%Y')
            for lease in customer.lease_agreements:
                if self.aggregate_lease_selected(lease):
                    if lease.po_number:
                        lease.aggregation_id = lease.po_number
                        po_numbers.append(lease.po_number)
                        aggregation_ids.append(lease.aggregation_id)
                    else:
                        if lease.ap_contact_ids:
                            ag_id = ''
                            for ap_id in lease.ap_contact_ids:
                                ag_id += str(ap_id.id)
                            lease.aggregation_id = ag_id
                            ap_groups.append(lease.ap_contact_ids)
                            aggregation_ids.append(ag_id)

                        else:
                            raise models.ValidationError(
                                'Leased agreement issue: Customer is marked for Aggregate '
                                'invoicing but lease agreement does not contain a PO or AP Contact')

            # make po_number list unique
            po_numbers = list(dict.fromkeys(po_numbers))
            aggregation_ids = list(dict.fromkeys(aggregation_ids))
            # find leases by PO
            for ags_id in aggregation_ids:
                line_ids = []
                lease_invoices = []
                unit_invoices = []
                leases = self.env['thomaslease.lease'].search(
                    [('aggregation_id', '=', ags_id), ('customer_id', '=', customer.id)])

                for lease in leases:
                    if self.aggregate_lease_selected(lease):

                        for line in lease.lease_lines:
                            product = line.product_id
                            invoice_line = self.env['account.invoice.line']

                            # create the invoice line
                            line_id = invoice_line.create({
                                'product_id': product.id,
                                'price_unit': line.total,
                                'quantity': 1,
                                'name': month + ' ' + year + ' - Monthly Lease: for Unit # ' + lease.vehicle_id.unit_no,
                                'invoice_line_tax_ids': line.tax_ids,
                                'account_id': product.property_account_income_id.id
                            })

                            # call set taxes to set them...otherwise the relationships aren't set properly
                            line_id._set_taxes()
                            line_id.price_unit = line.total
                            line_ids.append(line_id.id)
                            if lease.invoice_ids:
                                lease_invoices.extend(lease.invoice_ids.ids)
                            if lease.vehicle_id.lease_invoice_ids:
                                unit_invoices.extend(lease.vehicle_id.lease_invoice_ids.ids)

                a_invoice = accounting_invoice.create({
                    'partner_id': lease.customer_id.id,
                    'vehicle_id': lease.vehicle_id.id,
                    'date_invoice': the_wizard.invoice_date,
                    'date_due': the_wizard.invoice_due_date,
                    'type': 'out_invoice',
                    'state': 'draft',
                    'po_number': lease.po_number,
                    'invoice_line_ids': [(6, 0, line_ids)]
                })
                lease_invoices.append(a_invoice.id)
                unit_invoices.append(a_invoice.id)
                # set the invoice ids for the lease agreement
                for lease in leases:
                    if self.aggregate_lease_selected(lease):
                        lease.invoice_ids = [(6, 0, lease_invoices)]
                        for vehicle in lease.vehicle_id:
                            vehicle.with_context(skip_update=True).lease_invoice_ids = [(6, 0, unit_invoices)]

    @api.multi
    def record_lease_invoices(self):
        aggregate_customers = []

        for wizard in self:
            leases = wizard.lease_ids
            for lease in leases:
                # determine if an invoice already exists for the lease and don't create again...warn user
                lease.last_invoice_date = wizard.invoice_date
                a_lease = self.env['thomaslease.lease'].browse(lease)
                if a_lease.id.customer_id.aggregate_invoicing:

                    aggregate_customers.append(a_lease.id.customer_id)
                    print("Aggregate Customer: " + a_lease.id.customer_id.name)
                    # self.record_aggregate_invoice(a_lease,)
                else:
                    print("NORMAL INVOICING")
                    self.record_normal_invoice(a_lease, wizard)

            aggregate_customers = list(dict.fromkeys(aggregate_customers))
            self.record_aggregate_invoice(aggregate_customers, wizard)


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
