# -*- coding: utf-8 -*-

from odoo import models, fields, api
import requests, json, uuid, jsonpath
from urllib import parse

class ThomasAccountingInvoice(models.Model):

    _inherit = 'account.invoice'

    #department = fields.Char(string='Department')
    qc_check = fields.Boolean(string='Data Accuracy Validation')
    invoice_type = fields.Selection([('lease','Lease'),('maintenance', 'Maintenance')])
    vehicle_id = fields.Many2one("fleet.vehicle", string="Unit #")

    unit_no = fields.Char(related='vehicle_id.unit_no', string="Unit #")
    lease_ids = fields.Many2many('thomaslease.lease',string='Lease Agreements',
                                  relation='lease_agreement_account_invoice_rel')
    vehicle_ids = fields.Many2many('fleet.vehicle',string='Units',
                                  relation='unit_lease_account_invoice_rel')

    po_number = fields.Char(string='Purchase Order #')
    requires_manual_calculations = fields.Char(string="Needs Manual Calculation")
    invoice_from = fields.Date(string="Invoice From")
    invoice_to = fields.Date(string="Invoice To")
    invoice_posting_date = fields.Date(string="Invoice Posting Date")
    invoice_generation_date = fields.Date(string="Invoice Generation Date")



