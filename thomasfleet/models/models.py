# -*- coding: utf-8 -*-

from odoo import models, fields, api

class thomasfleet(models.Model):
    _inherit = 'fleet.vehicle'

    unit_no = fields.Char('Unit #')
    vin_id = fields.Char('V.I.N')
    #_name = 'thomasfleet.thomasfleet'

#     name = fields.Char()
#     value = fields.Integer()
#     value2 = fields.Float(compute="_value_pc", store=True)
#     description = fields.Text()
#
#     @api.depends('value')
#     def _value_pc(self):
#         self.value2 = float(self.value) / 100