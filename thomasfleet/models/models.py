# -*- coding: utf-8 -*-

from odoo import models, fields, api

class thomasfleet(models.Model):
    _inherit = 'fleet.vehicle'

    unit_no = fields.Char('Unit #')
    vin_id = fields.Char('V.I.N')
    trim_id = fields.Many2one('thomasfleet.trim', 'Trim', help='Trim for the Model of the vehicle' , domain="[('model_id','=',model_id)]")
    location = fields.Selection([('hamilton','Hamilton'),('selkirk', 'Selkirk'), ('niagara','Niagara')])
    notes = fields.Char('Notes');
    #_name = 'thomasfleet.thomasfleet'

class thomasfleetmodel(models.Model):
    _inherit = 'fleet.vehicle.model'

    trim_id = fields.One2many('thomasfleet.trim', 'model_id', 'Available Trims')

class thomasfleettrim(models.Model):
    _name = 'thomasfleet.trim'

    name = fields.Char('Trim Name')
    description = fields.Char('Description')
    model_id =  fields.Many2one('fleet.vehicle.model', 'Model' 'Available Trims')
    model_name = fields.Char(related='model_id.name')
    make_name = fields.Char(related='model_id.brand_id.name')


#     name = fields.Char()
#     value = fields.Integer()
#     value2 = fields.Float(compute="_value_pc", store=True)
#     description = fields.Text()
#
#     @api.depends('value')
#     def _value_pc(self):
#         self.value2 = float(self.value) / 100