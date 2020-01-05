# -*- coding: utf-8 -*-

from odoo import models, fields, api, _
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

    units_display = fields.Char(string='Unit #s', compute='_compute_units_display')
    po_number = fields.Char(string='Purchase Order #')
    requires_manual_calculations = fields.Char(string="Needs Manual Calculation")
    invoice_from = fields.Date(string="Invoice From")
    invoice_to = fields.Date(string="Invoice To")
    invoice_posting_date = fields.Date(string="Invoice Posting Date")
    invoice_generation_date = fields.Date(string="Invoice Generation Date")
    partner_shipping_id = fields.Many2one(
        'res.partner',
        string='Shipping Address',
        readonly=True,
        states={'draft': [('readonly', False)]},
        help="Delivery address for current invoice.")


    @api.onchange('partner_id', 'company_id')
    def _onchange_delivery_address(self):
        addr = self.partner_id.address_get(['delivery'])
        self.partner_shipping_id = addr and addr.get('delivery')

    def _compute_units_display(self):

        for rec in self:
            units = []
            for veh in rec.vehicle_ids:
                units.append(veh.unit_no)

            units =list(dict.fromkeys(units))
            rec.units_display = ',' .join(units)

    @api.multi
    def get_delivery_partner_id(self):
        self.ensure_one()
        return self.partner_shipping_id.id or super(ThomasAccountingInvoice, self).get_delivery_partner_id()

    @api.multi
    def _get_mail_contacts(self):

        self.ensure_one()
        contact_ids=[]
        for lease in self.lease_ids:
            contact_ids.extend(lease.ap_contact_ids.ids)
        return contact_ids

    @api.multi
    def action_invoice_cancel(self):
        self.ensure_one()
        self.move_name=False
        #leases = self.env['thomaslease.lease'].search([('id', 'in', self.lease_ids.ids)], limit=1)
        res =super(ThomasAccountingInvoice, self).action_invoice_cancel()
        for lease in self.lease_ids:
            invoice = self.env['account.invoice'].search([('id', 'in', lease.invoice_ids.ids),('state', '!=','cancel')], limit=1,order='date_invoice desc')
            lease.last_invoice_date = False
            lease.last_invoice_date = invoice.date_invoice
        return res

    @api.multi
    def unlink(self):
        for invoice in self:
            if invoice.state not in ('draft', 'cancel'):
                raise UserError(_(
                    'You cannot delete an invoice which is not draft or cancelled. You should create a credit note instead.'))
            elif invoice.move_name:
                raise UserError(_(
                    'You cannot delete an invoice after it has been validated (and received a number). You can set it back to "Draft" state and modify its content, then re-confirm it.'))

            for lease in invoice.lease_ids:
                the_invoice = self.env['account.invoice'].search([('id', 'in', lease.invoice_ids.ids),('state', '!=','cancel'), ('id', '!=', invoice.id)], limit=1,order='date_invoice desc')

                if the_invoice:
                    lease.last_invoice_date = invoice.date_invoice
                else:
                    lease.last_invoice_date = False

        return super(ThomasAccountingInvoice, self).unlink()


    @api.multi
    def action_invoice_sent(self):
        """ Open a window to compose an email, with the edi invoice template
            message loaded by default
        """
        self.ensure_one()
        res = super(ThomasAccountingInvoice,self).action_invoice_sent()
        ctx = res['context']
        res.update(context=dict(ctx,default_partner_ids=self._get_mail_contacts()))
        return res

        '''
        template = self.env.ref('account.email_template_edi_invoice', False)
        compose_form = self.env.ref('mail.email_compose_message_wizard_form', False)
        ctx = dict(
            default_model='account.invoice',
            default_res_id=self.id,
            default_use_template=bool(template),
            default_template_id=template and template.id or False,
            default_composition_mode='comment',
            default_partner_ids=self._get_mail_contacts(),
            mark_invoice_as_sent=True,
            custom_layout="account.mail_template_data_notification_email_account_invoice",
            force_email=True
        )
        return {
            'name': _('Compose Email'),
            'type': 'ir.actions.act_window',
            'view_type': 'form',
            'view_mode': 'form',
            'res_model': 'mail.compose.message',
            'views': [(compose_form.id, 'form')],
            'view_id': compose_form.id,
            'target': 'new',
            'context': ctx,
        }
        '''