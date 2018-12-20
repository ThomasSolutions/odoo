# -*- coding: utf-8 -*-

from odoo import models, fields, api

class ThomasContact(models.Model):
    _inherit = 'res.partner'
    department = fields.Char(string='Department')
    qc_check = fields.Boolean(string='Data Accuracy Validation')
    lease_agreements = fields.One2many('thomaslease.lease', 'customer_id', 'Lease Contracts')
    documents = fields.One2many('thomasfleet.customer_document', 'customer_id', 'Customer Docucments')

class ThomasCustomerDocument(models.Model):
    _name = 'thomasfleet.customer_document'

    customer_id = fields.Many2one("res.partner", "Customer")
    name = fields.Char("Name")
    description = fields.Char("Description")
    type = fields.Selection([('insurance', 'Proof of Insurance'), ('certification', 'Certification')])
    expiration = fields.Date('Expiration Date')
    document = fields.Binary("Document", attachment=True)
