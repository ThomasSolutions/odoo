# -*- coding: utf-8 -*-

from odoo import models, fields, api, tools, exceptions
import logging, pprint,requests,json,uuid,jsonpath
from datetime import date, datetime



def dump_obj(obj):
    fields_dict = {}
    for key in obj.fields_get():
        fields_dict[key] = obj[key]
    return fields_dict


class ThomasAsset(models.Model):
    _name = 'thomas.asset'
    unit_no = fields.Char('Unit #', track_visibility='onchange')
    notes = fields.Text('Notes', track_visibility='onchange')
    charge_code = fields.Char('Charge Code', track_visibility='onchange')
    filed_as = fields.Char("File As", track_visibility='onchange')
    company_acct = fields.Char("Company Acct", track_visibility='onchange')
    asset_class = fields.Many2one('thomasfleet.asset_class', 'Asset Class', track_visibility='onchange')
    insurance_class = fields.Many2one('thomasfleet.insurance_class', 'Insurance Class', track_visibility='onchange')
    thomas_purchase_price = fields.Float('Thomas Purchase Price', track_visibility='onchange')
    purchase_date = fields.Char('Purchase Date', track_visibility='onchange')
    usage = fields.Char('Usage', track_visibility='onchange')
    disposal_year = fields.Char('Disposal Year', track_visibility='onchange')
    disposal_date = fields.Char('Disposal Date', track_visibility='onchange')
    disposal_proceeds = fields.Float('Disposal Proceeds', track_visibility='onchange')
    sold_to = fields.Char('Sold To', track_visibility='onchange')
    betterment_cost = fields.Char("Betterment Cost", track_visibility='onchange')
    lease_status = fields.Many2one('thomasfleet.lease_status', 'Lease Status', track_visibility='onchange')
   # lease_status = fields.Selection([('spare','Spare'), ('maint_req','Maintenance Required'),('road_test','Road Test'),('detail','Detail'),('reserved','Customer/Reserved'),('leased', 'Leased'), ('available','Available for Lease'),('returned_inspect','Returned waiting Inspection')], 'Lease Status')
    photoSets = fields.One2many('thomasfleet.asset_photo_set', 'vehicle_id', 'Photo Set', track_visibility='onchange')
    inclusions = fields.Many2many('thomasfleet.inclusions', string='Inclusions', track_visibility='onchange')
    state = fields.Selection(
        [('spare', 'Spare'), ('maint_req', 'Maintenance Required'), ('road_test', 'Road Test'), ('detail', 'Detail'),
         ('reserved', 'Customer/Reserved'), ('leased', 'Leased'), ('available', 'Available for Lease'),
         ('returned_inspect', 'Returned waiting Inspection')], string="Status", default='available')


class ThomasAssetPhotoSet(models.Model):
    _name = 'thomasfleet.asset_photo_set'
    vehicle_id = fields.Many2one('fleet.vehicle', 'Vehicle')
    photoDate = fields.Date("Date")
    photos = fields.One2many('thomasfleet.asset_photo', 'photo_set_id', 'Photos')
    encounter = fields.Selection([('pickup', 'Pick Up'),('service', 'Service'),('return', 'Return')],'Encounter Type')

    @api.multi
    @api.depends('photoDate', 'encounter')
    def name_get(self):
        res = []
        for record in self:
            name = str(record.encounter) + "-"+ str(record.photoDate)
            res.append((record.id, name))
        return res

class ThomasAssetPhoto(models.Model):
    _name = 'thomasfleet.asset_photo'
    photo_set_id = fields.Many2one('thomasfleet.asset_photo_set', 'PhotoSet')
    position = fields.Selection([('driver side', 'Driver Side'), ('passenger side', 'Passenger Side'),
                                 ('front', 'Front'),('back', 'Back'),
                                 ('driver side front angle', 'Driver Side front Angle'),
                                 ('passenger side front angle', 'Passenger Side Front Angle'),
                                 ('driver side back angle', 'Driver Side Back Angle'),
                                 ('passenger side back angle', 'Passenger Side Back Angle')])
    image = fields.Binary("Image", attachment=True)
    image_small=fields.Binary("Small Image", attachment=True)
    image_medium=fields.Binary("Medium Image", attachment=True)

    @api.multi
    @api.depends('position')
    def name_get(self):
        res = []
        for record in self:
            name = record.position
            res.append((record.id, name))
        return res

    @api.model
    def create(self, vals):
        tools.image_resize_images(vals)
        return super(ThomasAssetPhoto, self).create(vals)

    @api.multi
    def write(self, vals):
        tools.image_resize_images(vals)
        return super(ThomasAssetPhoto, self).write(vals)

class ThomasFleetVehicle(models.Model):
    _name = 'fleet.vehicle'
    _inherit = ['thomas.asset', 'fleet.vehicle']
    _order = "unitInt asc"

    log = logging.getLogger('thomas')
    log.setLevel(logging.INFO)
    unitInt = fields.Integer(compute='_getInteger', store=True)

    def default_unit_no(self):
        last_vehicle = self.env['fleet.vehicle'].search([], limit=1, order='unitInt desc')
        print('Last Unit #' + last_vehicle.unit_no)
        return str(int(last_vehicle.unit_no) + 1)

    # thomas_asset = fields.Many2one('thomas.asset', ondelete='cascade')
    # fleet_vehicle = fields.Many2one('fleet.vehicle', ondelete='cascade')
    # name = fields.Char(compute='_compute_vehicle_name', store=True)

    #plate registration?
    unit_no = fields.Char("Unit #", default=default_unit_no, required=True, track_visibility='onchange')
    protractor_invoices = fields.One2many('thomasfleet.invoice','vehicle_id','Service Invoices')
    lease_agreements = fields.One2many('thomaslease.lease','vehicle_id', 'Lease Agreements')
    lease_invoice_ids = fields.Many2many('account.invoice',string='Invoices',
                                   relation='unit_lease_account_invoice_rel')
    lease_agreements_count = fields.Integer(compute='_compute_thomas_counts',string='Lease Agreements Count')
    lease_invoices_count = fields.Integer(compute='_compute_thomas_counts',string='Lease Invoices Count')
    unit_slug = fields.Char(compute='_compute_slug', readonly=True)
    vin_id = fields.Char('V.I.N', track_visibility='onchange')
    license_plate = fields.Char('License Plate', required=False, track_visibility='onchange')
    brand_id = fields.Many2one(related='model_id.brand_id', string='Make', track_visibility='onchange')

    model_id = fields.Many2one('fleet.vehicle.model', 'Model', required=True, help='Model of the vehicle',
                               domain="[('brand_id','=',brand_id)]",track_visibility='onchange')

    trim_id = fields.Many2one('thomasfleet.trim', string='Trim', help='Trim for the Model of the vehicle',
                              domain="[('model_id','=',model_id)]",track_visibility='onchange')
    location = fields.Many2one('thomasfleet.location', track_visibility='onchange')
    # fields.Selection([('hamilton', 'Hamilton'), ('selkirk', 'Selkirk'), ('niagara', 'Niagara')])
    door_access_code = fields.Char('Door Access Code', track_visibility='onchange')
    body_style = fields.Char('Body Style', track_visibility='onchange')
    drive = fields.Char('Drive', track_visibility='onchange')
    wheel_studs = fields.Char('Wheel Studs', track_visibility='onchange')
    wheel_size = fields.Char('Wheel Size', track_visibility='onchange')
    wheel_style = fields.Char('Wheel Style', track_visibility='onchange')
    wheel_base = fields.Char('Wheel Base', track_visibility='onchange')
    box_size = fields.Char('Box Size', track_visibility='onchange')
    seat_material = fields.Many2one('thomasfleet.seatmaterial', 'Seat Material', track_visibility='onchange')
    flooring = fields.Many2one('thomasfleet.floormaterial', 'Floor Material', track_visibility='onchange')
    trailer_hitch = fields.Selection([('yes', 'Yes'), ('no', 'No')], 'Trailer Hitch', default='yes', track_visibility='onchange')
    brake_controller = fields.Selection([('yes', 'Yes'), ('no', 'No')], 'Brake Controller', default='yes', track_visibility='onchange')
    tires = fields.Char('Tires', track_visibility='onchange')
    capless_fuel_filler = fields.Selection([('yes', 'Yes'), ('no', 'No')], 'Capless Fuel Filter', default='no', track_visibility='onchange')
    bluetooth = fields.Selection([('yes', 'Yes'), ('no', 'No')], 'Bluetooth', default='yes', track_visibility='onchange')
    navigation = fields.Selection([('yes', 'Yes'), ('no', 'No')], 'Navigation', default='no', track_visibility='onchange')
    warranty_start_date = fields.Char('Warranty Start Date', track_visibility='onchange')
    seat_belts = fields.Integer('# Seat Belts', track_visibility='onchange')
    seats = fields.Integer('# Seats', help='Number of seats of the vehicle', track_visibility='onchange')
    doors = fields.Integer('# Doors', help='Number of doors of the vehicle', default=5, track_visibility='onchange')
    # fuel_type = fields.Selection([('gasoline', 'Gasoline'), ('diesel', 'Diesel')],'Fuel Type', default='gasoline')
    notes = fields.Text(compute='_get_protractor_notes_and_owner', string='Protractor Notes', track_visibility='onchange')
    rim_bolts = fields.Char('Rim Bolts', track_visibility='onchange')
    engine = fields.Char('Engine', track_visibility='onchange')
    fuel_type = fields.Many2one('thomasfleet.fueltype', 'Fuel Type', track_visibility='onchange')
    fleet_status = fields.Many2one('fleet.vehicle.state', 'Fleet Status', track_visibility='onchange')
    air_conditioning = fields.Selection([('yes', 'Yes'), ('no', 'No')], 'Air Conditioning', default='yes', track_visibility='onchange')
    transmission = fields.Char("Transmission", track_visibility='onchange')
    protractor_guid = fields.Char(compute='protractor_guid_compute')
    stored_protractor_guid = fields.Char()#compute='get_protractor_guid')
    qc_check = fields.Boolean('Data Accurracy Validated')
    fin_check = fields.Boolean('Financial Accuracy Validated')
    accessories = fields.One2many('thomasfleet.accessory','vehicle_id',String="Accessories", track_visibility='onchange')
    write_to_protractor = fields.Boolean(default=False)
    production_date = fields.Char("Production Date", track_visibility='onchange')
    pulled_protractor_data = fields.Boolean(default=False,String="Got Data from Protractor")
    protractor_owner_guid = fields.Char(compute='_get_protractor_notes_and_owner', string= 'Protractor Owner ID')

    @api.multi
    @api.depends('unit_no')
    def name_get(self):
        if self._context.get('lease'):
            res = []
            for record in self:
                name = record.unit_no
                res.append((record.id, name))
            return res
        else:
            print("Context is none")
            return super(ThomasFleetVehicle, self).name_get()

    @api.model
    def _name_search(self, name='', args=None, operator='ilike', limit=100, name_get_uid=None):

        args = [] if args is None else args.copy()
        if not (name == '' and operator == 'ilike'):
            args += ['|',
                ('name', operator, name),
                ('unit_no', operator, name)]

        return super(ThomasFleetVehicle, self)._name_search(
            name='', args=args, operator='ilike',
            limit=limit, name_get_uid=name_get_uid)



    @api.depends('unit_no')
    def _getInteger(self):
        for rec in self:
            try:
                int(rec.unit_no)
                rec.unitInt = int(rec.unit_no)
            except ValueError:
                rec.unitInt = 0
                raise models.ValidationError('Protractor Unit # ' + rec.unit_no
                                             + ' is not valid (it must be an integer)')


    # accessories = fields.Many2many()
    #@api.depends('stored_protractor_guid')
    def protractor_guid_compute(self):
        if self:
            print('HERE IS THE STORED PGUID:' + str(self.stored_protractor_guid))

        for record in self:
           # print('Computing GUID ' + str(record.stored_protractor_guid))
            if not record.stored_protractor_guid:
                guid = record.get_protractor_id()

                #record.stored_protractor_guid = guid['id']
                if guid:
                    #print('Retrieved GUID' + guid['id'])
                    if guid['id']:
                        record.protractor_guid = guid['id']
                    #record.with_context(skip_update=True).stored_protractor_guid = guid['id']
                        record.with_context(skip_update=True).update({'stored_protractor_guid': guid['id']})
                    else:
                        print("Problem with GUID in protractor")
                        record.protractor_guid = 'Unable to locate Unit by VIN in Protractor'
                else:
                    print("Could NOT Retrieve GUID")
                    record.protractor_guid = 'Unable to locate Unit by VIN in Protractor'
            else:
                record.protractor_guid = record.stored_protractor_guid

    def _generateProtractorNotes(self):
        if self.notes:
            p_notes = self.notes
        else:
            p_notes = "Body Style: " + str(self.body_style) + "\r\n" + "Drive: " + str(self.drive) + "\r\n" + "Flooring: " +\
                  str(self.flooring.name)+ "\r\n" + "Wheel Base: " + str(self.wheel_base) + "\r\n" + "Box Size: " + \
                  str(self.box_size) + "\r\n" + "Seat Type: " + str(self.seat_material.name) + "\r\n" + "Seat Belts: " + \
                  str(self.seat_belts) + "\r\n" + "Trailer Hitch: " + str(self.trailer_hitch) + "\r\n" + \
                  "Brake Controller: " + str(self.brake_controller) + "\r\n" + "Tires: " + str(self.tires) + "\r\n" + \
                  "Fuel Type: " + str(self.fuel_type.name) + "\r\n" + \
                  "Location: " + str(self.location.name) + "\r\n" + \
                  "Door Access Code: " + str(self.door_access_code) + "\r\n" + \
                  "Wheel Studs: " + str(self.wheel_studs) + "\r\n" + \
                  "Rim Bolts: " + str(self.rim_bolts) + "\r\n" + \
                  "Capless Fuel Filter: " + str(self.capless_fuel_filler) + "\r\n" + \
                  "Bluetooth: " + str(self.bluetooth) + "\r\n" + \
                  "Navigation: " + str(self.navigation) + "\r\n"

        return p_notes



    @api.depends('unit_no', 'model_id')
    def _compute_slug(self):
        for record in self:

            if record.unit_no and record.model_id:
                record.unit_slug = 'Unit # - ' + record.unit_no + '-' + record.model_id.brand_id.name + '/' + record.model_id.name
            else:
                record.unit_slug = 'Unit # - '

    def _compute_thomas_counts(self):
        the_agreements = self.env['thomaslease.lease']
        the_invoices = self.env['account.invoice']
        for record in self:
            record.lease_agreements_count = the_agreements.search_count([('vehicle_id', '=', record.id)])
            record.lease_invoices_count = the_invoices.search_count([('vehicle_id', '=', record.id)])


    def update_protractor(self):
        url = " "
        if self.stored_protractor_guid:
            url = "https://integration.protractor.com/IntegrationServices/1.0/ServiceItem/"+self.stored_protractor_guid

        else:
            if self.protractor_guid:
                url = "https://integration.protractor.com/IntegrationServices/1.0/ServiceItem/" + self.protractor_guid
            else:
                url = "bad guid"

        vin = self.vin_id
        plateReg = "ON"
        unit = self.unit_no
        #self.protractor_guid
        if self.protractor_owner_guid:
            owner_id = self.protractor_owner_guid
        else:
            owner_id = "43e0319c-41bc-40c3-be47-336b9e0afaa1"
        theUnit = {
            "VIN":self.vin_id,
            "PlateRegistration":"ON",
            "ID":self.stored_protractor_guid,
            "IsComplete":True,
            "Unit":self.unit_no,
            "Color": self.color,
            "Year": self.model_year,
            "Make": self.model_id.brand_id.name,
            "Model": self.model_id.name,
            "Submodel":self.trim_id.name,
            "Engine": self.engine,
            "Type":"Vehicle",
            "Lookup":self.license_plate,
            "Description": self.unit_slug,
            "Usage": int(self.odometer),
            "ProductionDate":"",
            "Note": self._generateProtractorNotes(),
            "NoEmail": False,
            "NoPostCard": False,
            "PreferredContactMethod":"Email",
            "MarketingSource":"",
            "OwnerID": owner_id
            }
        payload =json.dumps(theUnit)
        #print(payload)
            #"{\"IsComplete\": true,\"PlateRegistration\": \""+plateReg+"\",
        # \"VIN\": \"2C4RDGBGXDR542491\",\"Unit\": \"\",\"Color\": \"PURPLE\",
        # \"Year\": 2013,\"Make\": \"Dodge\",\"Model\": \"Grand Caravan\",
        # \"Submodel\": \"SE\",\"Engine\": \"V6 3.6L 3604CC 220CID\",\"ID\":
        # \"a70c552f-5555-4a57-b4ea-8dbb798e7013\",\"Type\": \"Vehicle\",
        # \"Lookup\": \"BRDA497\",\"Description\": \"2013 Dodge Grand Caravan SE\",
        # \"Usage\": 0,\"ProductionDate\": \"0001-01-01T00:00:00\",\"Note\": \"\",
        # \"NoEmail\": false,\"NoPostCard\": false,\"PreferredContactMethod\": \"Email\",\"MarketingSource\":\"\"}"
        '''
        headers = {
            'connectionId': "de8b3762edfd41fdbc37ddc3ef4d0f1d",
            'apiKey': "3d326387107942f0bf5fa9ec342e4989",
            'authentication': "5NmTG0A6uNLnTiVcp1FZL9is+js=",
            'Accept': "application/json",
            'Content-Type': "application/json",
            'Cache-Control': "no-cache",
            'Postman-Token': "2e5fe1e2-b08e-41b8-aab1-58b75642351a"
        }
        '''
        headers = {
            'connectionId': "8c3d682f873644deb31284b9f764e38f",
            'apiKey': "fb3c8305df2a4bd796add61e646f461c",
            'authentication': "S2LZy0munq81s/uiCSGfCvGJZEo=",
            'Accept' : "application/json",
            'Content-Type': "application/json"
        }
        response = requests.request("POST", url, data=payload, headers=headers)

        #print(payload)
    @api.one
    def get_protractor_id(self):
        #print("IN GET PROTRACTOR ID for" + str(self.vin_id))
        self.log.info("Getting Protarctor ID for Vehicle: "+ str(self.vin_id))
        the_resp = {'id': False, 'update': False}
        if self.vin_id:
            url = "https://integration.protractor.com/IntegrationServices/1.0/ServiceItem/Search/"+self.vin_id
            headers = {
            'connectionId': "8c3d682f873644deb31284b9f764e38f",
            'apiKey': "fb3c8305df2a4bd796add61e646f461c",
            'authentication': "S2LZy0munq81s/uiCSGfCvGJZEo=",
            'Accept': "application/json"
            }
            response = requests.request("GET", url, headers=headers)

            self.log.info("JSON RESPONSE FROM PROTRACTOR" + response.text)
            data = response.json()
            the_id= False
            color=""
            for item in data['ItemCollection']:
                the_id = item['ID']

            self.log.info("JSON RESPONSE FROM PROTRACTOR ID" + the_id)
            if not the_id:
                the_id = uuid.uuid4()
                the_resp={'id':the_id,'update':True}
                self.log.info("Setting Write to protractor cause no id found")
            else:
                self.log.info("Found an existing unit: "+the_id)
                the_resp = {'id':the_id,'update':False}
                 #this can only be set on create
                
        self.log.info("RETURNING THE RESPONSE " + the_resp)
        return the_resp

    @api.multi
    def write(self, values):
        #we only want to update protractor if the unit doesn't exist the firt time
        #subsequent updates should happen

        print("IN WRITE FUNCTION")

        record = super(ThomasFleetVehicle,self).write(
            values)

        #self.message_post(body=values)

        print("Loop Breaker" + str(self.env.context.get('skip_update')))
        if self.env.context.get('skip_update'):
            print("BUSTING OUT")

        else:
            print("updating protractor")
            self.update_protractor()


        #ThomasFleetVehicle_write.get_protractor_id()

        return record


    @api.model
    def create(self, data):
        print ("IN CREATE FUNCTION")
        '''
        self.log.info('CREATING THIS THING')
        last_vehicle = self.env['fleet.vehicle'].search([], limit=1, order='unit_no')
        self.log.info('last Vehicle Name %s', last_vehicle.name)
        attr = vars(last_vehicle)
        self.log.info(dump_obj(last_vehicle))
        record = super(ThomasFleetVehicle, self).create(data)
        self.log.info('Unit # %s', record.unit_no)
        right_now_yr = int(date.today().strftime('%y'))
        if not record.unit_no:
            self.log.info("Inside the if")
            if last_vehicle.unit_no:
                cur_unit_no_yr = int(last_vehicle.unit_no[0:2])
                self.log.info('Unit Yr %d', cur_unit_no_yr)
                if right_now_yr - cur_unit_no_yr == 0:
                    record.unit_no = str(int(last_vehicle.unit_no) + 1)
                else:
                    record.unit_no = str(right_now_yr * 100)
            else:
                record.unit_no = str(right_now_yr * 100)
        '''

        self = self.with_context(skip_update=True)


        print("before create")

        res = super(ThomasFleetVehicle, self).create(data)

        print("after create")
        guid= res.get_protractor_id()
        #print("GUID UDPATE VALUE" + str(guid['update']))
        if guid:
            if guid['update']:
                self = self.with_context(skip_update=False)
                res.with_context(self).stored_protractor_guid = guid['id']
            else:
                res.stored_protractor_guid = guid['id']


        #print("UPDATED CONTEXT" + str(self.env.context.get('skip_update')))


        print("after setting guid")

        return res

    @api.onchange('vin_id')
    @api.one
    def _get_protractor_data(self):
        print("GETTING PROTRACTOR DATA")
        the_resp = "NO VIN"
        if self.vin_id:
            url = "https://integration.protractor.com/IntegrationServices/1.0/ServiceItem/Search/" + self.vin_id
            headers = {
                'connectionId': "8c3d682f873644deb31284b9f764e38f",
                'apiKey': "fb3c8305df2a4bd796add61e646f461c",
                'authentication': "S2LZy0munq81s/uiCSGfCvGJZEo=",
                'Accept': "application/json",
                'Cache-Control': "no-cache",
                'Postman-Token': "9caffd55-2bac-4e79-abfc-7fd1a3e84c6d"
            }
            response = requests.request("GET", url, headers=headers)

            #logging.info(response.text)
            data = response.json()
            the_note = ""

            for item in data['ItemCollection']:
                the_note = item['Note']
                plate_reg = item['PlateRegistration']
                vin = item['VIN']
                unit = item['Unit']
                color = item['Color']
                year = item['Year']
                themake = item['Make']
                themodel = item['Model']
                thesubmodel = item['Submodel']
                engine = item['Engine']
                plate = item['Lookup']
                description = item['Description']
                usage = item['Usage']
                proddate = item['ProductionDate']
                ownerid = item['OwnerID']

                self.notes = the_note
                #self.vin_id = vin
                # "PlateRegistration": "ON",
                # "ID": self.stored_protractor_guid,
                # "IsComplete": True,
                # "Unit": self.unit_no,
                self.unit_no = unit
                self.color = color
                self.model_year = year
                self.odometer = int(usage)

                the_brand = self.env['fleet.vehicle.model.brand'].search([('name', '=ilike', themake)])
                if the_brand:
                    self.brand_id = the_brand.id
                else:
                    brand_data={'name':themake}
                    the_new_brand = self.env['fleet.vehicle.model.brand'].create(brand_data)
                    self.brand_id = the_new_brand.id

                the_model = self.env['fleet.vehicle.model'].search([('brand_id', '=', the_brand.id),('name', '=ilike', themodel)])
                if the_model:
                    self.model_id = the_model.id
                else:
                    model_data={'name': themodel, 'brand_id':self.brand_id.id}
                    the_new_model = self.env['fleet.vehicle.model'].create(model_data)
                    self.model_id = the_new_model.id

                the_trim = self.env['thomasfleet.trim'].search([('brand_id', '=', the_brand.id),('model_id', '=', the_model.id),('name', '=ilike', thesubmodel)])
                if the_trim:
                    print("Found Trim "+ the_trim.name)
                    self.trim_id = the_trim.id
                else:
                    trim_data = {'name':thesubmodel, 'model_id':self.model_id.id, 'brand_id': self.brand_id.id}
                    the_new_trim = self.env['thomasfleet.trim'].create(trim_data)
                    self.trim_id = the_new_trim.id

                self.engine = engine
                self.license_plate = plate
                self.production_date = proddate
                self.pulled_protractor_data = True
                self.protractor_owner_guid = ownerid
                # "Usage": int(self.odometer),

                result ={'warning': {
                    'title': 'Vehicle VIN is in Protractor',
                    'message': 'Found an existing vechile with this VIN in Protractor.  The data has been copied to the form, changes will be saved back to protractor'
                }}
                return result

    @api.depends('stored_protractor_guid')
    @api.one
    def _get_protractor_notes_and_owner(self):
        the_resp = "NO VIN"
        if self.vin_id:
            url = "https://integration.protractor.com/IntegrationServices/1.0/ServiceItem/Search/"+self.vin_id
            headers = {
            'connectionId': "8c3d682f873644deb31284b9f764e38f",
            'apiKey': "fb3c8305df2a4bd796add61e646f461c",
            'authentication': "S2LZy0munq81s/uiCSGfCvGJZEo=",
            'Accept': "application/json",
            'Cache-Control': "no-cache",
            'Postman-Token': "9caffd55-2bac-4e79-abfc-7fd1a3e84c6d"
            }
            response = requests.request("GET", url, headers=headers)


            data = response.json()
            the_note=""
            the_ownerID=""

            for item in data['ItemCollection']:
                the_note = item['Note']
                the_ownerID = item['OwnerID']

            for record in self:
                record.notes = the_note
                record.protractor_owner_guid = the_ownerID




    @api.one
    def _get_protractor_invoices(self):
        url = "https://integration.protractor.com/IntegrationServices/1.0/ServiceItem/"+str(self.stored_protractor_guid)+"/Invoice"
        da = datetime.now()
        querystring = {" ": "", "startDate": "2014-11-01", "endDate": da.strftime("%Y-%m-%d"), "%20": ""}

        headers = {
            'connectionId': "8c3d682f873644deb31284b9f764e38f",
            'apiKey': "fb3c8305df2a4bd796add61e646f461c",
            'authentication': "S2LZy0munq81s/uiCSGfCvGJZEo=",
            'Accept': "application/json",
            'cache-control': "no-cache",
            'Postman-Token': "7c083a2f-d5ce-4c1a-aa35-8da253b61bee"
        }

        response = requests.request("GET", url, headers=headers, params=querystring)
        print("INVOICE DATA " + response.text)
        data = response.json()

        updatedInvoices = []
        invoices = self.protractor_invoices

        for a in invoices:
            invoiceFound = False
            for i in data['ItemCollection']:
                print("Invoice Numbers:::"+ str(a.invoiceNumber) +"=="+ str(i['InvoiceNumber']))
                if a.invoiceNumber == i['InvoiceNumber']:
                    print("Found ID " + a.id)
                    invoiceFound = True

            if not invoiceFound:
                print("Invoice Not Found# " + a.invoiceNumber)
                updatedInvoices.append((2,a.id,0))

        for item in data['ItemCollection']:
            inv={'vehicle_id': self.id,
                 'invoice_guid' : item['ID'],
                 'protractor_guid': self.stored_protractor_guid,
                 'workOrderNumber': item['WorkOrderNumber'],
                 'invoiceNumber': item['InvoiceNumber']}
            if 'Summary' in item:
                inv['grandTotal'] = item['Summary']['GrandTotal']
                inv['netTotal'] = item['Summary']['NetTotal']
                inv['laborTotal'] = item['Summary']['LaborTotal']
                inv['partsTotal'] = item['Summary']['PartsTotal']
                inv['subletTotal'] = item['Summary']['SubletTotal']
            invDT = str(item['InvoiceTime']).split("T")
            inv['invoiceDate']= invDT[0]
            inv['invoiceTime']= invDT[1]
            if 'Technician' in item:
                inv['technichan'] = str(item['Technician']['Name'])
            if 'ServiceAdvisor' in item:
                inv['serviceAdvisor'] = str(item['ServiceAdvisor']['Name'])
            if 'Header' in item:
                per =str(item['Header']['LastModifiedBy'])
                uName = per.split("\\")
                #print(uName)
                inv['lastModifiedBy'] = uName[1]


            invoiceNotFound=True
            invObj = self.env['thomasfleet.invoice'].create(inv)
            invDetsArr = invObj.get_invoice_details_rest()
            inv['invoice_details'] = invDetsArr
            for invoice in invoices:
                if invoice.invoiceNumber == item['InvoiceNumber']:
                    updatedInvoices.append((1, invoice.id, inv))
                    invoiceNotFound = False

            if invoiceNotFound:
                updatedInvoices.append((0,0,inv))



        print("Updated Invoices" + str(updatedInvoices))
        self.update({'protractor_invoices': updatedInvoices})





    @api.multi
    def act_show_vehicle_photos(self):
        """ This opens log view to view and add new log for this vehicle, groupby default to only show effective costs
            @return: the costs log view
        """
        self.ensure_one()
        res = self.env['ir.actions.act_window'].for_xml_id('thomasfleet', 'thomas_asset_photos_action')
        res.update(
            context=dict(self.env.context, default_vehicle_id=self.id, search_default_parent_false=True),
            domain=[('vehicle_id', '=', self.id)]
        )
        print("Unit"+str(self.unit_no))
        for aSet in self.photoSets:
            print("ENCOUNTER" + aSet.encounter)
        return res



    @api.multi
    def act_show_vehicle_lease_agreements(self):
        """ This opens log view to view and add new log for this vehicle, groupby default to only show effective costs
            @return: the costs log view
        """
        self.ensure_one()
        res = self.env['ir.actions.act_window'].for_xml_id('thomasfleet', 'thomas_lease_agreements_action')
        res.update(
            #context=dict(self.env.context, default_vehicle_id=self.id, search_default_parent_false=True),
            domain=[('vehicle_id', '=', self.id)]
        )
        print("Unit" + str(self.unit_no))

        return res

    def act_show_vehicle_lease_invoices(self):
        """ This opens log view to view and add new log for this vehicle, groupby default to only show effective costs
            @return: the costs log view
        """
        self.ensure_one()
        res = self.env['ir.actions.act_window'].for_xml_id('thomasfleet', 'thomas_lease_invoices_action')
        res.update(
            #context=dict(self.env.context, default_vehicle_id=self.id, search_default_parent_false=True),
            domain=[('vehicle_id', '=', self.id)]
        )
        print("Unit" + str(self.unit_no))

        return res

    @api.multi
    def act_get_invoices(self):
        print("INVOICE ACTION")
        print('SELF ID ' + str(self.id))
        for rec in self:
            if rec.protractor_invoices:  # don't add invoices right now if there are some
                for inv in rec.protractor_invoices:
                    print("NOT DELETING INVOICE:::" + str(inv.invoiceNumber))
                    #inv.unlink()

        self._get_protractor_invoices()


        #for rec in self:
            #for inv in rec.protractor_invoices:
                #inv.get_invoice_details()

        self.ensure_one()
        res = self.env['ir.actions.act_window'].for_xml_id('thomasfleet', 'thomas_invoice_action')
        res.update(
        context=dict(self.env.context, default_vehicle_id=self.id, search_default_parent_false=True),
        domain=[('vehicle_id', '=', self.id)]
        )
        return res

class ThomasFleetOdometer(models.Model):
    _inherit= 'fleet.vehicle.odometer'
    lease_id = fields.Many2one('thomaslease.lease', 'Lease Agreement')
    customer_id =fields.Many2one(related="lease_id.customer_id", string="Customer", readonly=True)
    activity = fields.Selection([('lease_out', 'Lease Start'), ('lease_in', 'Lease Return'),('service', 'Service'),('swap', 'Swap')], string="Activity", track_visibility='onchange')

class ThomasFleetVehicleModel(models.Model):
    _inherit = 'fleet.vehicle.model'

    name = fields.Char('Model name', required=True)
    trim_id = fields.One2many('thomasfleet.trim', 'model_id', 'Available Trims')

    @api.multi
    @api.depends('name')
    def name_get(self):
        res = []
        for record in self:
            name = record.name
            res.append((record.id, name))
        return res




class ThomasFleetTrim(models.Model):
    _name = 'thomasfleet.trim'

    name = fields.Char('Trim Name')
    description = fields.Char('Description')
    brand_id = fields.Many2one(related='model_id.brand_id', string='Make')

    model_id = fields.Many2one('fleet.vehicle.model', required=True, string='Model', help='Model of the vehicle',
                               domain="[('brand_id','=',brand_id)]")

    #model_name = fields.Char(related='model_id.name')
    #make_name = fields.Char(related='model_id.brand_id.name')

class ThomasFleetLeaseStatus(models.Model):
    _name = 'thomasfleet.lease_status'
    name = fields.Char('Lease Status')
    description = fields.Char('Description')

class ThomasFleetLocation(models.Model):
    _name = 'thomasfleet.location'

    name = fields.Char('Location')
    description = fields.Char('Description')


class ThomasFleetSeatMaterial(models.Model):
    _name = 'thomasfleet.seatmaterial'

    name = fields.Char('Seat Material')
    description = fields.Char('Description')


class ThomasFleetFloorMaterial(models.Model):
    _name = 'thomasfleet.floormaterial'
    name = fields.Char('Floor Material')
    description = fields.Char('Description')


class ThomasFleetFuelType(models.Model):
    _name = 'thomasfleet.fueltype'

    name = fields.Char('Fuel Type')
    description = fields.Char('Description')


class ThomasFleetAssetClass(models.Model):
    _name = 'thomasfleet.asset_class'

    name = fields.Char('Asset Class')
    description = fields.Char('Description')


class ThomasFleetInsuranceClass(models.Model):
    _name = 'thomasfleet.insurance_class'

    name = fields.Char('Insurance Class')
    description = fields.Char('Description')

class ThomasFleetInclusions(models.Model):
    _name = 'thomasfleet.inclusions'

    name = fields.Char('Inclusion')
    description = fields.Char('Description')
    inclusion_cost= fields.Float('Cost')
    inclusion_charge=fields.Float('Monthly Rate')

class ThomasFleetInvoiceClass(models.Model):
    _name = 'thomasfleet.invoice'
    _res = []
    vehicle_id = fields.Many2one('fleet.vehicle', 'Vehicle')
    invoice_details = fields.One2many('thomasfleet.invoice_details', 'invoice_id',  'Invoice Details')
    protractor_guid = fields.Char('Protractor GUID',related='vehicle_id.protractor_guid')
    invoiceTime = fields.Char('Invoice Time')
    invoiceDate = fields.Char('Invoice Date')
    technichan = fields.Char('Technichan')
    serviceAdvisor = fields.Char('Service Advisor')
    lastModifiedBy = fields.Char('Last Modified By')
    workOrderNumber = fields.Char('Work Order Number')
    invoiceNumber = fields.Char('Invoice Number')
    partsTotal = fields.Float('Parts Total')
    subletTotal= fields.Float('Sublet Total')
    grandTotal=fields.Float('Grand Total')
    laborTotal=fields.Float('Labor Total')
    netTotal=fields.Float('Net Total')
    invoice_guid = fields.Char('Invoice Guid')

    def get_invoice_details_rest(self):
        url = "https://integration.protractor.com/IntegrationServices/1.0/Invoice/" + str(self.invoice_guid)

        headers = {
            'connectionId': "8c3d682f873644deb31284b9f764e38f",
            'apiKey': "fb3c8305df2a4bd796add61e646f461c",
            'authentication': "S2LZy0munq81s/uiCSGfCvGJZEo=",
            'Accept': "application/json",
            'cache-control': "no-cache",
            'Postman-Token': "7c083a2f-d5ce-4c1a-aa35-8da253b61bee"
        }

        response = requests.request("GET", url, headers=headers)
        data = response.json()
        # inv_det_model = self.env['thomasfleet.invoice_details']
        for invDets in self.invoice_details:
            for invDetLine in invDets:
                invDetLine.unlink()
            invDets.unlink()
        # recs = inv_det_model.search(['invoice_id','=', self.id])

        sp_lines = []
        '''
        for r in recs:
            r.unlink()

        inv_det_line_model = self.env['thomasfleet.invoice_details_line']

        l_recs = inv_det_line_model.search(['invoice_id','=', self.id])

        for l in l_recs:
            l.unlink()
        '''

        work_order_num = data['WorkOrderNumber']
        inv_num = data['InvoiceNumber']
        inv_guid = data['ID']

        for sp in data['ServicePackages']['ItemCollection']:
            inv_detail = {'title': sp['ServicePackageHeader']['Title'],
                          'description': sp['ServicePackageHeader']['Description'],
                          'invoice_number': inv_num,
                          'work_order_number': work_order_num,
                          'invoice_guid': inv_guid
                          }

            for spd in sp['ServicePackageLines']['ItemCollection']:
                inv_detail_line = {'invoice_number': inv_num,
                                   'work_order_number': work_order_num,
                                   'invoice_guid': inv_guid,
                                   'complete': spd.get('Completed'),
                                   'rank': spd.get('Rank'),
                                   'type': spd.get('Type'),
                                   'description': spd.get('Description'),
                                   'quantity': spd.get('Quantity'),
                                   'unit': spd.get('Unit'),
                                   'rate_code': spd.get('Rate Code'),
                                   'price': spd.get('Price'),
                                   'price_unit': spd.get('PriceUnit'),
                                   'minimum_charge': spd.get('Minimum Charge'),
                                   'total': spd.get('Total'),
                                   'discount': spd.get('Discount'),
                                   'extended_total': spd.get('Exteneded Total'),
                                   'total_cost': spd.get('Total Cost'),
                                   'other_charge_code': spd.get('Other Charge Code'),
                                   'tags': spd.get('Tags'),
                                   'flag': spd.get('Flag'),
                                   'technician_name': spd.get('Technician'),
                                   'service_advisor': spd.get('Service Advisor')
                                   }

                sp_lines.append((0, 0, inv_detail_line))

            inv_detail['line_items'] = sp_lines

        return [(0, 0, inv_detail)]

    def get_invoice_details(self):

        url = "https://integration.protractor.com/IntegrationServices/1.0/Invoice/"+str(self.invoice_guid)

        headers = {
            'connectionId': "8c3d682f873644deb31284b9f764e38f",
            'apiKey': "fb3c8305df2a4bd796add61e646f461c",
            'authentication': "S2LZy0munq81s/uiCSGfCvGJZEo=",
            'Accept': "application/json",
            'cache-control': "no-cache",
            'Postman-Token': "7c083a2f-d5ce-4c1a-aa35-8da253b61bee"
        }

        response = requests.request("GET", url, headers=headers)
        data = response.json()
        #inv_det_model = self.env['thomasfleet.invoice_details']
        for invDets in self.invoice_details:
            for invDetLine in invDets:
                invDetLine.unlink()
            invDets.unlink()
        #recs = inv_det_model.search(['invoice_id','=', self.id])

        sp_lines = []
        '''
        for r in recs:
            r.unlink()

        inv_det_line_model = self.env['thomasfleet.invoice_details_line']

        l_recs = inv_det_line_model.search(['invoice_id','=', self.id])

        for l in l_recs:
            l.unlink()
        '''

        work_order_num = data['WorkOrderNumber']
        inv_num = data['InvoiceNumber']
        inv_guid = data['ID']

        for sp in data['ServicePackages']['ItemCollection']:
            inv_detail = {'title': sp['ServicePackageHeader']['Title'],
                          'description': sp['ServicePackageHeader']['Description'],
                          'invoice_number': inv_num,
                          'work_order_number':work_order_num,
                          'invoice_guid':inv_guid
                          }

            for spd in sp['ServicePackageLines']['ItemCollection']:
                inv_detail_line ={'invoice_number': inv_num,
                                  'work_order_number': work_order_num,
                                  'invoice_guid': inv_guid,
                                  'complete': spd.get('Completed'),
                                  'rank': spd.get('Rank'),
                                  'type': spd.get('Type'),
                                  'description': spd.get('Description'),
                                  'quantity': spd.get('Quantity'),
                                  'unit': spd.get('Unit'),
                                  'rate_code': spd.get('Rate Code'),
                                  'price': spd.get('Price'),
                                  'price_unit': spd.get('PriceUnit'),
                                  'minimum_charge': spd.get('Minimum Charge'),
                                  'total': spd.get('Total'),
                                  'discount':spd.get('Discount'),
                                  'extended_total': spd.get('Exteneded Total'),
                                  'total_cost': spd.get('Total Cost'),
                                  'other_charge_code': spd.get('Other Charge Code'),
                                  'tags': spd.get('Tags'),
                                  'flag': spd.get('Flag'),
                                  'technician_name': spd.get('Technician'),
                                  'service_advisor': spd.get('Service Advisor')
                                  }

                sp_lines.append((0,0,inv_detail_line))

            inv_detail['line_items']= sp_lines
            self.invoice_details = [(0, 0, inv_detail)]


            #inv_det_model.create(inv_detail)
            #i_details = []
            #i_details.append((0,0,the_details))


            #self.update({'invoice_details': inv_detail})

    @api.multi
    def act_get_invoice_details(self):
        print("FIRED OF INVOICE DETAILS ACTION")
        for rec in self:
            if rec.invoice_details:  # don't add invoices right now if there are some
                for inv_det in rec.invoice_details:
                    print("UNLINKING  INVOICE:::" + str(inv_det.invoice_id))
                    inv_det.unlink()
        self.ensure_one()
        self.get_invoice_details()

        res = self.env['ir.actions.act_window'].for_xml_id('thomasfleet', 'thomas_invoice_details_action')
        res.update(
            context=dict(self.env.context, default_invoice_id=self.id, search_default_parent_false=True),
            domain=[('invoice_id', '=', self.id)]
        )
        return res

    @api.multi
    def generate_account_invoices(self):
        print ("Genearting Account Invoices")


class ThomasFleetInvoiceDetails(models.Model):
    _name = 'thomasfleet.invoice_details'
    invoice_id = fields.Many2one('thomasfleet.invoice', 'Invoice')
    line_items = fields.One2many('thomasfleet.invoice_details_line', 'invoice_details_id', 'Invoice Details Line')
    invoice_number = fields.Char('Invoice Number')
    work_order_number = fields.Char('Work Order Number')
    title = fields.Char('Title')
    description = fields.Char('Description')
    type = fields.Char('Type')
    quantity = fields.Char('Quantity')
    rate = fields.Char('Rate')
    total = fields.Char('Total')
    invoice_guid = fields.Char('Invoice Guid')

    @api.multi
    def act_get_invoice_details_line(self):
        #for rec in self:
            #if rec.line_items:  # don't add invoices right now if there are some
                #for inv_item in rec.line_items:
                    #print("Unlinking INVOICE:::" + str(inv_item.invoice_guid))
                    #inv_item.unlink()
            #self.ensure_one()
        #self.get_invoice_details()

        res = self.env['ir.actions.act_window'].for_xml_id('thomasfleet', 'thomas_invoice_details_line_action')
        res.update(
            context=dict(self.env.context, default_invoice_id = self.id, search_default_parent_false=True),
            domain=[('invoice_details_id', '=', self.id)]
         )
        return res



class ThomasFleetInvoiceLine(models.Model):
    _name = 'thomasfleet.invoice_details_line'
    invoice_details_id = fields.Many2one('thomasfleet.invoice_details', 'Invoice Details')
    complete = fields.Boolean('Complete')
    rank = fields.Integer('Rank')
    type = fields.Char('Type')
    description = fields.Char('Description')
    quantity = fields.Float('Quantity')
    unit = fields.Char('Unit')
    rate_code = fields.Char('Rate Code')
    price = fields.Float('Price')
    price_unit = fields.Char('PriceUnit')
    minimum_charge = fields.Float('Minimum Charge')
    total = fields.Float('Total')
    discount = fields.Float('Discount')
    extended_total = fields.Float('Extended Total')
    total_cost = fields.Float('Total Cost')
    other_charge_code = fields.Char('Other Charge Code')
    tags = fields.Char('Tags')
    flag = fields.Char('Flag')
    technician_name = fields.Char('Technician')
    service_advisor = fields.Char('Service Advisor')
    invoice_number =  fields.Char('Invoice Number')
    work_order_number = fields.Char('Work Order Number')
    invoice_guid = fields.Char('Invoice Guid')

class ThomasFleetAccessoryType(models.Model):
    _name='thomasfleet.accessory_type'
    name = fields.Char("Accessory Type")

class ThomasFleetAccessory(models.Model):
    _name = 'thomasfleet.accessory'

    vehicle_id = fields.Many2one('fleet.vehicle', 'Vehicle')
    name = fields.Char('Accessory Name')
    description = fields.Char('Description')
    unit_no = fields.Char('Accessory #')
    thomas_purchase_price = fields.Float('Thomas Purchase Price')
    accessory_charge = fields.Float('Monthly Rate')
    purchase_date = fields.Date('Purchase Date')
    type = fields.Many2one('thomasfleet.accessory_type', 'Accessory Type')

    @api.multi
    @api.depends('type')
    def name_get(self):
            res = []
            for record in self:
                if record.type.id == 12:
                    name = record.name + " " + record.unit_no
                    res.append((record.id, name))
                else:
                    res.append((record.id,record.name))
            return res



class ThomasFleetMXInvoiceWizard(models.TransientModel):
    _name = 'thomasfleet.mx.invoice.wizard'
    lease_ids = fields.Many2many('thomaslease.lease', string="Lease")
    invoice_date = fields.Date(string="Invoice Date")

    @api.multi
    def record_lease_invoices(self):
        accounting_invoice = self.env['account.invoice']
        for wizard in self:
            leases = wizard.lease_ids
            for lease in leases:
                #determine if an invoice already exists for the lease and don't create again...warn user
                print("Accounting Invoice Create " +str(wizard.invoice_date) + " : "+ lease.id)
                #accounting_invoice.create({}) need to match customer to accounting invoice etc