# -*- coding: utf-8 -*-

from odoo import models, fields, api


class ThomasLease(models.Model):
    _name = 'thomaslease.lease'
    lease_number = fields.Char('Lease ID',readonly=True)
    po_number = fields.Char("Purchase Order #")
    lease_status = fields.Many2one('thomasfleet.lease_status', 'Lease Status')
    lease_start_date = fields.Date("Rental Period is from")
    min_lease_end_date = fields.Date("To")
    monthly_rate = fields.Float("Monthly Rate")
    monthly_mileage = fields.Integer("Monthly Mileage")
    mileage_overage_rate =fields.Float("Additional Mileage Charge")
    customer_id = fields.Many2one("res.partner", "Customer")
    vehicle_id = fields.Many2one("fleet.vehicle", "Vehicle")
    unit_no = fields.Char('Unit #',related="vehicle_id.unit_no",readonly=True)
    inclusions = fields.Many2many(related="vehicle_id.inclusions", string="Inclusions", readonly=True)
    accessories = fields.One2many(related="vehicle_id.accessories", string="Accessories", readonly=True)
   # inclusions_base_rate = fields.Float(compute="_calcBaseIncRate", string="Inclusion List Rate")
    inclusions_discount = fields.Float('Inclusion Discount')
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

    @api.model
    def create(self, data):
        record = super(ThomasLease, self).create(data)
        Agreements = self.env['thomaslease.lease']
        aCount = 0
        if record.customer_id:
            aCount = Agreements.search_count([('customer_id', '=', record.customer_id.id)])

        record.lease_number = str(record.customer_id.name)+"_"+str(record.unit_no)+"_"+str(record.lease_start_date)+"_"+str(aCount)

        return record
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
