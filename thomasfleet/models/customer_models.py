# -*- coding: utf-8 -*-

from odoo import models, fields, api
import requests, json, uuid, jsonpath
from urllib import parse

class ThomasContact(models.Model):

    _inherit = 'res.partner'



    department = fields.Char(string='Department')
    qc_check = fields.Boolean(string='Data Accuracy Validation')
    lease_agreements = fields.One2many('thomaslease.lease', 'customer_id', 'Lease Contracts')
    documents = fields.One2many('thomasfleet.customer_document', 'customer_id', 'Customer Docucments')
    protractor_guid = fields.Char(string='Protractor GUID' , readonly=True) #,compute='_compute_protractor_guid')

    @api.multi
    def find_protractor_guid(self):

        default_company_id = self.env['res.company']._company_default_get().id
        for record in self:

            #print("Getting Protarctor ID for Customer: "+ str(parse.quote(str(record.name_get()))))
            the_resp = "NO GUID"
            if record.id != default_company_id:# and not record.protractor_guid:
                if record.name:
                    print("IN GET PROTRACTOR ID for" + str(self.name_get()))
                    url = "https://integration.protractor.com/IntegrationServices/1.0/Contact/Search/" + parse.quote(record.name)
                    headers = {
                        'connectionId': "8c3d682f873644deb31284b9f764e38f",
                        'apiKey': "fb3c8305df2a4bd796add61e646f461c",
                        'authentication': "S2LZy0munq81s/uiCSGfCvGJZEo=",
                        'Accept': "application/json"
                    }
                    response = requests.request("GET", url, headers=headers)
                    print(str(response.status_code))
                    if response.ok:
                        #print(response.text)
                        data = response.json()
                        the_id = False
                        for item in data['ItemCollection']:
                            the_id = item['ID']

                        if not the_id:
                            the_id = uuid.uuid4()
                            the_resp = the_id
                            print("Setting Write to protractor cause no id found")
                        else:
                            print("Found an existing unit: " + the_id)
                            the_resp = the_id
                            # this can only be set on create
                    else:
                        the_resp = "Can't locate: " + self.name
            else:
                the_resp = record.protractor_guid
            record.protractor_guid = the_resp

class ThomasCustomerDocument(models.Model):
    _name = 'thomasfleet.customer_document'

    customer_id = fields.Many2one("res.partner", "Customer")
    name = fields.Char("Name")
    description = fields.Char("Description")
    type = fields.Selection([('insurance', 'Proof of Insurance'), ('certification', 'Certification')])
    expiration = fields.Date('Expiration Date')
    document = fields.Binary("Document", attachment=True)
