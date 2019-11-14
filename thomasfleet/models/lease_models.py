# -*- coding: utf-8 -*-

from odoo import models, fields, api, exceptions
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
                    for sel in lines.product_id._fields['rate_type'].base_field.selection:
                        if sel[0] == lines.product_id.rate_type:
                            the_str = sel[1]
                    if rate_str == '':
                        rate_str += str(the_str)
                    else:
                        rate_str += ', ' + str(the_str)
                else:
                    rate_str = 'NO SET'
            rec.rate_type = rate_str


    def _search_rate_type(self, operator, value):
        lease_ids = []
        records = self.env['thomaslease.lease'].search([])
        for rec in records:
            if 'not' in operator or '!' in operator:
                if not rec.rate_type:
                    lease_ids.append(rec.id)
                if rec.rate_type != value:
                    lease_ids.append(rec.id)
            else:
                if rec.rate_type:
                    if value:
                        if value in rec.rate_type:
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
            rel_next_month = start_of_current_month + relativedelta.relativedelta(months=+1)
            start_of_next_month = rel_next_month#date(lease_start_date.year, int(lease_start_date.month + 1), 1)
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
                last_day_lease_month = calendar.monthrange(today.year, today.month)[1]
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

    lease_start_date = fields.Date("Lease Start Date")  # , required=True)

    billing_start_date = fields.Date("Billing Start Date")

    invoice_from = fields.Date(string="Invoice From")
    invoice_to = fields.Date(string="Invoice To")
    last_invoice_to = fields.Date(string="Last Invoice Date Range")
    invoice_posting_date = fields.Date(string="Invoice Posting Date")
    invoice_generation_date = fields.Date(string="Invoice Generation Date")
    invoice_due_date = fields.Date(string="Invoice Due Date")

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

    monthly_rate = fields.Float("Monthly Rate", change_default=True)
    weekly_rate = fields.Float("Weekly Rate")
    daily_rate = fields.Float("Daily Rate")
    monthly_tax = fields.Float("Tax(HST-13%)")
    monthly_total = fields.Float("Monthly Lease Total")
    monthly_mileage = fields.Integer("Monthly Mileage Allowance", default=3500)
    mileage_overage_rate = fields.Float("Additional Mileage Rate", default=0.14)

    customer_id = fields.Many2one("res.partner", "Customer", change_default=True)  # required=True)

    vehicle_id = fields.Many2one("fleet.vehicle", string="Unit #", change_default=True)  # required=True)

    unit_slug = fields.Char("Unit", related="vehicle_id.unit_slug", readonly=True)
    lease_lines = fields.One2many('thomaslease.lease_line', 'lease_id', string='Lease Lines', change_default=True,
                                  copy=True, auto_join=True)
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
    rate_type = fields.Char("Rate Type", compute='_get_rate_type', search='_search_rate_type', change_default=True)
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
        #self.daily_rate = (self.monthy_rate * .125)
        #self.weekly_rate = (self.monthly_rate * .45)


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
        leases_ids = self.env.context.get('active_ids')
        for lease in leases_ids:
            a_lease = self.env['thomaslease.lease'].browse(lease)
            self.set_invoice_dates(a_lease)

        return leases_ids

    def set_invoice_dates(self, lease):
        dt = datetime.now()

        l_rdt = False
        if lease.lease_return_date:
            l_rdt = datetime.strptime(lease.lease_return_date, '%Y-%m-%d')

        if lease.billing_start_date:
            l_sdt = datetime.strptime(lease.billing_start_date, '%Y-%m-%d')
        elif lease.lease_start_date:
            l_sdt = datetime.strptime(lease.lease_start_date, '%Y-%m-%d')
        else:
            raise models.UserError('Lease Start Date or Billing Date Not set for: ' + lease.lease_number)

        if "Dofasco" in lease.customer_id.name:
            i_from = datetime(dt.year, dt.month - 1, 1)
            days_in_month = calendar.monthrange(dt.year, dt.month - 1)[1]
            i_to = datetime(dt.year, dt.month - 1, days_in_month)
        else:
            i_from = datetime(dt.year, dt.month, 1)
            days_in_month = calendar.monthrange(dt.year, dt.month)[1]
            i_to = datetime(dt.year, dt.month, days_in_month)

        # if start date - handled by initial invoicing
        # if return date
        if l_rdt:
            if i_to.month == l_rdt.month and i_to.year == l_rdt.year:
                if l_rdt.day < i_to.day:
                    i_to = l_rdt

        if l_sdt > i_from:
            i_from = lease.billing_start_date

        lease.invoice_from = i_from
        lease.invoice_to = i_to
        lease.invoice_due_date = dt + relativedelta.relativedelta(days=+30)
        lease.invoice_generation_date = dt
        lease.invoice_posting_date = dt

    def _default_invoice_date(self):
        return datetime.now()

    def _default_invoice_due_date(self):
        df = datetime.now()
        dt2 = df + relativedelta.relativedelta(days=+30)
        return dt2

    def _default_invoice_posting_date(self):
        dt2 = datetime.now()
        dt = date(dt2.year, dt2.month - 1, 1)
        return dt

    def _default_invoice_start_date(self):
        df = datetime.now()
        dt2 = date(df.year, df.month - 1, 1)
        return dt2

    def _default_invoice_end_date(self):
        df = datetime.now()
        days_in_month = calendar.monthrange(df.year, df.month - 1)[1]
        dt2 = date(df.year, df.month - 1, days_in_month)
        return dt2

    @api.onchange("invoice_date")
    def set_dates(self):
        # todo: add non-amd calc..
        # if not amd invoice is for the current of the invoice date..
        # else amd is previous month.
        # todo: posting date same invoice date
        # todo: update lease agreement table to include from and to and invoice date and due date (30 days from invoice date)
        # todo: posting date can be removed

        # todo:  initialInvoice...only invoice if it's retured
        # todo: otherwise invoice for it in the next month cycle..or when returned
        '''
        dt = datetime.strptime(self.invoice_date, '%Y-%m-%d')
        end_of_month = calendar.monthrange(dt.year, dt.month)[1]
        end_of_prev_month = calendar.monthrange(dt.year, dt.month-1)[1]
        self.invoice_posting_date = date(dt.year,dt.month,end_of_month)
        self.invoice_due_date = date(dt.year, dt.month,end_of_month)
        self.invoice_start_date = date(dt.year, dt.month-1,1)
        self.invoice_end_date = date(dt.year,dt.month-1,end_of_prev_month)
        '''

    def calc_biweekly_lease(self, biweekly_rate, lease):
        # calculate invoice for 4 weeks from last date.
        last_to_date = datetime.strptime(lease.last_invoice_to, '%Y-%m-%d')
        start_date = last_to_date
        if lease.lease_return_date:
            end_date = datetime.strptime(lease.lease_return_date, '%Y-%m-%d')
        else:
            end_date = start_date + relativedelta.relativedelta(weeks=+4)

        num_days = (end_date - start_date).days
        daily_rate = (biweekly_rate * 2) / num_days
        amount = daily_rate * num_days

        return amount

    def calc_rate_monthly_lease(self, monthly_total, start_date, end_date):

        start_d = datetime.strptime(start_date, '%Y-%m-%d')
        end_d = datetime.strptime(end_date, '%Y-%m-%d')
        num_days = (end_d - start_d).days
        daily_rate = (monthly_total * 12.5) / 100
        weekly_rate = (monthly_total * 45) / 100
        days_in_month = calendar.monthrange(end_d.year, end_d.month)[1]
        amount = monthly_total

        if num_days < 7:
            amount = num_days * daily_rate
        elif num_days >= 7 and num_days < days_in_month:
            days = num_days % 7
            weeks = math.floor(num_days / 7)
            amount = (days * daily_rate) + (weeks * weekly_rate)
            if amount > monthly_total:
                amount = monthly_total

        return amount

    def calc_rate_weekly_lease(self, weekly_total, start_date, end_date):

        start_d = datetime.strptime(start_date, '%Y-%m-%d')
        end_d = datetime.strptime(end_date, '%Y-%m-%d')
        num_days = (end_d - start_d).days
        monthly_rate = (weekly_total /0.45)
        daily_rate = (monthly_rate * 12.5)/100
        days_in_month = calendar.monthrange(end_d.year, end_d.month)[1]
        amount = monthly_rate

        if num_days < 7:
            amount = num_days * daily_rate
        elif num_days >= 7 and num_days < days_in_month:
            days = num_days % 7
            weeks = math.floor(num_days / 7)
            amount = (days * daily_rate) + (weeks * weekly_total)
            if amount > monthly_rate:
                amount = monthly_rate

        return amount

    def calc_rate_weekly_lease(self, daily_total, start_date, end_date):

        start_d = datetime.strptime(start_date, '%Y-%m-%d')
        end_d = datetime.strptime(end_date, '%Y-%m-%d')
        num_days = (end_d - start_d).days
        monthly_rate = (daily_total /0.125)
        weekly_rate = (monthly_rate * 45)/100
        days_in_month = calendar.monthrange(end_d.year, end_d.month)[1]
        amount = monthly_rate

        if num_days < 7:
            amount = num_days * daily_total
        elif num_days >= 7 and num_days < days_in_month:
            days = num_days % 7
            weeks = math.floor(num_days / 7)
            amount = (days * daily_total) + (weeks * weekly_rate)
            if amount > monthly_rate:
                amount = monthly_rate

        return amount
    # add weekly, add day, add term
    # todo figure out how to go from daily to weekly to monthly

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
                the_amt = (days * pu_daily) + (weeks * pu_weekly)
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
                the_amt = (days * cc_daily) + (weeks * cc_weekly)
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
                amount = (days * ts_daily) + (weeks * ts_weekly)

        if rate_type == 'amd_daily_tr':
            if num_days < 7:
                amount = num_days * tr_daily
            elif num_days >= 7 and num_days < days_in_month:
                days = num_days % 7
                weeks = math.floor(num_days / 7)
                amount = (days * tr_daily) + (weeks * tr_weekly)

        if rate_type == 'amd_daily_ft':
            amount = (num_days / days_in_month) * ft_monthly

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

    def calculate_line_amount(self, product, line_amount, start_date, end_date, lease):

        print("CALC AMOUNT FOR : " + product.categ_id.name)
        the_amount = line_amount
        if lease.lease_return_date:
            end_date = lease.lease_return_date

        if product.rate_type == 'monthly':
            the_amount = self.calc_rate_monthly_lease(line_amount, start_date, end_date)
        elif product.rate_type == 'weekly':
            the_amount = self.calc_rate_weekly_lease(line_amount, start_date, end_date)
        elif product.rate_type == 'daily':
            the_amount = self.calc_rate_daily_lease(line_amount, start_date, end_date)
        elif product.rate_type == 'biweekly':
            the_amount = self.calc_biweekly_lease(line_amount, lease)
        elif 'amd' in product.rate_type:
            the_amount = self.calc_amd_rate(product.rate_type, line_amount, start_date, end_date)
        elif 'stelco' in product.rate_type:
            the_amount = self.calc_stelco_rate(product.rate_type, line_amount, start_date, end_date)

        return the_amount


    _name = 'thomaslease.lease.invoice.wizard'
    lease_ids = fields.Many2many('thomaslease.lease', string="Lease", default=_default_lease_ids)
    invoice_date = fields.Date(string="Invoice Date", default=_default_invoice_date)
    invoice_due_date = fields.Date(string="Invoice Due Date", default=_default_invoice_due_date)
    invoice_posting_date = fields.Date(string="Invoice Posting Date", default=_default_invoice_posting_date)
    invoice_start_date = fields.Date(string="Invoice From", default=_default_invoice_start_date)
    invoice_end_date = fields.Date(string="Invoice To", default=_default_invoice_end_date)

    def aggregate_lease_selected(self, a_lease):
        resp = False
        for lease in self.lease_ids:
            if a_lease.id == lease.id:
                resp = True
        return resp

    def determine_last_invoice_to(self, lease):
        last_to_date = datetime.strptime(lease.invoice_to, '%Y-%m-%d')
        end_date = last_to_date + relativedelta.relativedelta(months=+1)
        if lease.lease_return_date:
            end_date = datetime.strptime(lease.lease_return_date, '%Y-%m-%d')
        elif lease.rate_type == 'bi-weekly':
            end_date = last_to_date + relativedelta.relativedelta(weeks=+4)

        return end_date
    '''
    def create_invoice_description(self, lease, line_amount, line):

        start_date = datetime.strptime(lease.invoice_from, '%Y-%m-%d').date()
        end_date = datetime.strptime(lease.id.invoice_to, '%Y-%m-%d').date()

        num_days = (end_date - start_date).days
        pro_rated = ''
        if line_amount < line.price:
            description = 'Lease for Unit # ' + the_lease.id.vehicle_id.unit_no + ' for ' + month + ' ' + str(
                start_date.day) + ' to ' + str(
                end_date.day) + ' ' + year
        else:
            description = month + ' ' + year + ' - Monthly Lease: for Unit # ' + lease.vehicle_id.unit_no
    '''

    @api.multi
    def record_normal_invoice2(self, the_lease):
        accounting_invoice = self.env['account.invoice']

        line_ids = []
        next_month_line_ids = []
        lease_invoices = the_lease.id.invoice_ids.ids
        unit_invoices = the_lease.id.vehicle_id.lease_invoice_ids.ids
        month = datetime.strptime(the_lease.id.invoice_from, '%Y-%m-%d').strftime('%b')
        year = datetime.strptime(the_lease.id.invoice_from, '%Y-%m-%d').strftime('%Y')
        dt_inv_to = datetime.strptime(the_lease.id.invoice_to, '%Y-%m-%d')
        end_of_month = calendar.monthrange(dt_inv_to.year, dt_inv_to.month)[1]

        if the_lease.id.run_initial_invoicing:
            last_to_date = datetime.strptime(the_lease.id.invoice_to, '%Y-%m-%d')
            prev_relative_month = last_to_date + relativedelta.relativedelta(months=-1)

            prev_month_from = datetime.strptime(the_lease.id.billing_start_date, '%Y-%m-%d')
            prev_month_days = calendar.monthrange(prev_relative_month.year, prev_relative_month.month)[1]
            prev_month_to = datetime(prev_relative_month.year, prev_relative_month.month, prev_month_days)
            prev_month = prev_month_from.strftime('%b')
            prev_year = prev_month_from.strftime('%Y')

        for line in the_lease.id.lease_lines:
            product = line.product_id
            invoice_line = self.env['account.invoice.line']
            line_amount = self.calculate_line_amount(product, line.price, the_lease.id.invoice_from,
                                                     the_lease.id.invoice_to, the_lease.id)

            start_date = datetime.strptime(the_lease.id.invoice_from, '%Y-%m-%d').date()
            end_date = datetime.strptime(the_lease.id.invoice_to, '%Y-%m-%d').date()

            num_days = (end_date - start_date).days
            pro_rated = ''
            quantity = 1

            if num_days <= end_of_month:
                description = 'Lease for Unit # ' + the_lease.id.vehicle_id.unit_no + ' - ' + month + ' ' + str(
                    start_date.day) + ' to ' + str(
                    end_date.day) + ' ' + year
            elif the_lease.id.rate_type == 'Bi-Weekly':
                last_to_date = datetime.strptime(the_lease.id.last_invoice_to, '%Y-%m-%d')
                start_date = last_to_date + relativedelta.relativedelta(days=+1)

                if the_lease.id.lease_return_date:
                    end_date = datetime.strptime(the_lease.id.lease_return_date, '%Y-%m-%d')
                else:
                    end_date = last_to_date + relativedelta.relativedelta(weeks=+4)

                start_date_str = start_date.strftime('%b %d')
                end_date_str = end_date.strftime('%b %d')
                description = 'Bi Weekly Lease for Unit # ' + the_lease.id.vehicle_id.unit_no + ' for ' + \
                              start_date_str + ' to ' + end_date_str + ', ' + year
                line_amount = line.price
                quantity = 2
            else:
                description = month + ' ' + year + ' - Monthly Lease: for Unit # ' + the_lease.id.vehicle_id.unit_no

            line_id = invoice_line.create({
                'product_id': product.id,
                'price_unit': line_amount,
                'quantity': quantity,
                'name': description,
                'invoice_line_tax_ids': [line.tax_ids],
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
            'date_invoice': the_lease.id.invoice_generation_date,
            'date_due': the_lease.id.invoice_due_date,
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
                                                              prev_month_from.strftime('%Y-%m-%d'),
                                                              prev_month_to.strftime('%Y-%m-%d'), the_lease.id)

                num_days = (prev_month_to - prev_month_from).days
                pro_rated = prev_month + ' ' + prev_year
                quantity =1
                if num_days <= prev_month_days:
                    description = 'Lease for Unit # ' + the_lease.id.vehicle_id.unit_no + ' - ' + prev_month + ' ' + str(
                        prev_month_from.day) + ' to ' + str(
                        prev_month_to.day) + ' ' + prev_year
                elif the_lease.id.rate_type == 'Bi-Weekly':#need to determine what to do here
                    last_to_date = datetime.strptime(the_lease.id.last_invoice_to, '%Y-%m-%d')
                    start_date = last_to_date + relativedelta.relativedelta(days=+1)

                    if the_lease.id.lease_return_date:
                        end_date = datetime.strptime(the_lease.id.lease_return_date, '%Y-%m-%d')
                    else:
                        end_date = last_to_date + relativedelta.relativedelta(weeks=+4)

                    start_date_str = start_date.strftime('%b %d')
                    end_date_str = end_date.strftime('%b %d')
                    description = 'Bi Weekly Lease for Unit # ' + the_lease.id.vehicle_id.unit_no + ' for ' + \
                                  start_date_str + ' to ' + end_date_str + ', ' + year
                    next_line_amount = next_line.price
                    quantity = 2
                else:
                    description = prev_month + ' ' + prev_year + ' - Monthly Lease: for Unit # ' + the_lease.id.vehicle_id.unit_no

                next_month_line_id = invoice_line.create({
                    'product_id': product.id,
                    'price_unit': next_line_amount,
                    'quantity': quantity,
                    'name': description,
                    'invoice_line_tax_ids': next_line.tax_ids,
                    'account_id': product.property_account_income_id.id
                })

                next_month_line_id._set_taxes()
                next_month_line_id.price_unit = next_line_amount

                next_month_line_ids.append(next_month_line_id.id)

            a_next_invoice = accounting_invoice.create({
                'partner_id': the_lease.id.customer_id.id,
                'vehicle_id': the_lease.id.vehicle_id.id,
                'date_invoice': the_lease.id.invoice_generation_date,
                'date_due': the_lease.id.invoice_due_date,
                'invoice_from': prev_month_from,
                'invoice_to': prev_month_to,
                'invoice_posting_date': the_lease.id.invoice_generation_date,
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
        the_lease.id.last_invoice_to = self.determine_last_invoice_to(the_lease.id)



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
                next_month_line_ids = []
                lease_invoices = []
                unit_invoices = []
                leases = self.env['thomaslease.lease'].search(
                    [('aggregation_id', '=', ags_id), ('customer_id', '=', customer.id)])

                for lease in leases:
                    if self.aggregate_lease_selected(lease):
                        dt_inv_to = datetime.strptime(lease.invoice_to, '%Y-%m-%d')
                        end_of_month = calendar.monthrange(dt_inv_to.year, dt_inv_to.month)[1]
                        if lease.run_initial_invoicing:
                            last_to_date = datetime.strptime(lease.invoice_to, '%Y-%m-%d')
                            prev_relative_month = last_to_date + relativedelta.relativedelta(months=-1)

                            prev_month_from = datetime.strptime(lease.billing_start_date, '%Y-%m-%d')
                            prev_month_days = calendar.monthrange(prev_relative_month.year, prev_relative_month.month)[
                                1]
                            prev_month_to = datetime(prev_relative_month.year, prev_relative_month.month,
                                                     prev_month_days)
                            prev_month = prev_month_from.strftime('%b')
                            prev_year = prev_month_from.strftime('%Y')

                        for line in lease.lease_lines:
                            product = line.product_id
                            invoice_line = self.env['account.invoice.line']
                            line_amount = self.calculate_line_amount(product, line.price, lease.invoice_from,
                                                                     lease.invoice_to, lease.id)
                            start_date = datetime.strptime(lease.invoice_from, '%Y-%m-%d').date()
                            end_date = datetime.strptime(lease.invoice_to, '%Y-%m-%d').date()

                            num_days = (end_date - start_date).days
                            quantity = 1

                            if num_days <= end_of_month:
                                description = 'Lease for Unit # ' + lease.vehicle_id.unit_no + ' - ' + month + ' ' + str(
                                    start_date.day) + ' to ' + str(
                                    end_date.day) + ' ' + year
                            elif lease.rate_type == 'Bi-Weekly':
                                last_to_date = datetime.strptime(lease.last_invoice_to, '%Y-%m-%d')
                                start_date = last_to_date + relativedelta.relativedelta(days=+1)

                                if lease.lease_return_date:
                                    end_date = datetime.strptime(lease.lease_return_date, '%Y-%m-%d')
                                else:
                                    end_date = last_to_date + relativedelta.relativedelta(weeks=+4)

                                start_date_str = start_date.strftime('%b %d')
                                end_date_str = end_date.strftime('%b %d')
                                description = 'Bi Weekly Lease for Unit # ' + lease.vehicle_id.unit_no + ' for ' + \
                                              start_date_str + ' to ' + end_date_str + ', ' + year
                                line_amount = line.price
                                quantity = 2
                            else:
                                description = month + ' ' + year + ' - Monthly Lease: for Unit # ' + lease.vehicle_id.unit_no

                            # create the invoice line
                            line_id = invoice_line.create({
                                'product_id': product.id,
                                'price_unit': line_amount,
                                'quantity': quantity,
                                'name': description,
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

                        if lease.run_initial_invoicing:
                            for next_line in lease.lease_lines:
                                next_line_amount = self.calculate_line_amount(product, next_line.price,
                                                                              prev_month_from.strftime('%Y-%m-%d'),
                                                                              prev_month_to.strftime('%Y-%m-%d'), lease)

                                num_days = (prev_month_to - prev_month_from).days
                                pro_rated = prev_month + ' ' + prev_year
                                quantity = 1
                                if num_days <= prev_month_days:
                                    description = 'Lease for Unit # ' + lease.vehicle_id.unit_no + ' - ' + prev_month + ' ' + str(
                                        prev_month_from.day) + ' to ' + str(
                                        prev_month_to.day) + ' ' + prev_year
                                elif lease.rate_type == 'Bi-Weekly':  # need to determine what to do here
                                    last_to_date = datetime.strptime(lease.last_invoice_to, '%Y-%m-%d')
                                    start_date = last_to_date + relativedelta.relativedelta(days=+1)

                                    if lease.lease_return_date:
                                        end_date = datetime.strptime(lease.lease_return_date, '%Y-%m-%d')
                                    else:
                                        end_date = last_to_date + relativedelta.relativedelta(weeks=+4)

                                    start_date_str = start_date.strftime('%b %d')
                                    end_date_str = end_date.strftime('%b %d')
                                    description = 'Bi Weekly Lease for Unit # ' + lease.vehicle_id.unit_no + ' for ' + \
                                                  start_date_str + ' to ' + end_date_str + ', ' + year
                                    next_line_amount = next_line.price
                                    quantity = 2
                                else:
                                    description = prev_month + ' ' + prev_year + ' - Monthly Lease: for Unit # ' + lease.vehicle_id.unit_no

                                next_month_line_id = invoice_line.create({
                                    'product_id': product.id,
                                    'price_unit': next_line_amount,
                                    'quantity': quantity,
                                    'name': description,
                                    'invoice_line_tax_ids': next_line.tax_ids,
                                    'account_id': product.property_account_income_id.id
                                })

                                next_month_line_id._set_taxes()
                                next_month_line_id.price_unit = next_line_amount

                                next_month_line_ids.append(next_month_line_id.id)

                            a_next_invoice = accounting_invoice.create({
                                'partner_id': lease.customer_id.id,
                                'vehicle_id': lease.vehicle_id.id,
                                'date_invoice': lease.invoice_generation_date,
                                'date_due': lease.invoice_due_date,
                                'invoice_from': prev_month_from,
                                'invoice_to': prev_month_to,
                                'invoice_posting_date': lease.invoice_generation_date,
                                'invoice_generation_date': lease.invoice_generation_date,
                                'type': 'out_invoice',
                                'state': 'draft',
                                'po_number': lease.po_number,
                                'requires_manual_calculations': lease.requires_manual_calculations,
                                'invoice_line_ids': [(6, 0, next_month_line_ids)]
                            })

                            lease_invoices.append(a_next_invoice.id)
                            unit_invoices.append(a_next_invoice.id)

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
                        lease.run_initial_invoicing = False
                        lease.last_invoice_to = self.determine_last_invoice_to(lease)

                        for vehicle in lease.vehicle_id:
                            vehicle.with_context(skip_update=True).lease_invoice_ids = [(6, 0, unit_invoices)]

    @api.multi
    def record_lease_invoices(self):
        aggregate_customers = []

        for wizard in self:
            leases = wizard.lease_ids
            for lease in leases:
                # determine if an invoice already exists for the lease and don't create again...warn user

                a_lease = self.env['thomaslease.lease'].browse(lease)
                if a_lease.id.customer_id.aggregate_invoicing:

                    aggregate_customers.append(a_lease.id.customer_id)
                    print("Aggregate Customer: " + a_lease.id.customer_id.name)
                    # self.record_aggregate_invoice(a_lease,)
                else:
                    print("NORMAL INVOICING")
                    # self.record_normal_invoice(a_lease, wizard)
                    self.record_normal_invoice2(a_lease)
                lease.last_invoice_date = wizard.invoice_date
            aggregate_customers = list(dict.fromkeys(aggregate_customers))
            self.record_aggregate_invoice(aggregate_customers, wizard)

        theMess = self.env['thomaslease.message']
        rec = theMess.create({'message': 'Invoice(s) have been created for ' + self.invoice_date})

        return {

            'name': 'Lease Invoice Creation',

            'type': 'ir.actions.act_window',

            'res_model': 'thomaslease.message',

            'res_id': rec.id,

            'view_mode': 'form',

            'view_type': 'form',

            'target': 'new'

        }


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
