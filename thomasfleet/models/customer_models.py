# -*- coding: utf-8 -*-

from odoo import models, fields, api

class ThomasContact(models.Model):
    _inherit = 'res.partner'
    department = fields.Char(string='Department')
    qc_check = fields.Boolean(string='Data Accuracy Validation')
    lease_agreements = fields.One2many('thomaslease.lease', 'customer_id', 'Lease Contracts')
