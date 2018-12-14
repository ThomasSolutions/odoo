# -*- coding: utf-8 -*-

from odoo import models, fields, api


class ThomasLease(models.Model):
    _name = 'thomaslease.lease'
    lease_number = fields.Char("Lease Number")
    lease_status = fields.Selection([('active','Active'),('closed','Closed')])
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
'''
    @api.depends('inclusions')
    def __calcBaseIncRate(self):

        Agreements = self.env['thomasfleet.inclusion']
        for record in self:
            res = Agreements.search([('vehicle_id', '=', record.id)])
            for inc in res:
                record.inclusions
'''
