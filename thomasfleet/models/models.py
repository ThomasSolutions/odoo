# -*- coding: utf-8 -*-

from odoo import models, fields, api, tools, exceptions
import logging, pprint,requests,json,uuid,jsonpath
from datetime import date, datetime
from dateutil import parser

_unit_inv = []

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
    lease_status = fields.Many2one('thomasfleet.lease_status', 'Rental Agreement Status', track_visibility='onchange')
   # lease_status = fields.Selection([('spare','Spare'), ('maint_req','Maintenance Required'),('road_test','Road Test'),('detail','Detail'),('reserved','Customer/Reserved'),('leased', 'Leased'), ('available','Available for Lease'),('returned_inspect','Returned waiting Inspection')], 'Lease Status')
    photoSets = fields.One2many('thomasfleet.asset_photo_set', 'vehicle_id', 'Photo Set', track_visibility='onchange')
    inclusions = fields.Many2many('thomasfleet.inclusions', string='Inclusions', track_visibility='onchange')
    state = fields.Selection(
        [('spare', 'Spare'), ('maint_req', 'Maintenance Required'), ('road_test', 'Road Test'), ('detail', 'Detail'),
         ('reserved', 'Customer/Reserved'), ('leased', 'Rented'), ('available', 'Available for Rent'),
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
        print('Last Unit #' + str(last_vehicle.unit_no))
        return str(int(last_vehicle.unit_no) + 1)

    @api.multi
    @api.onchange('maintenance_cost_to_date')
    def set_cost_report(self):
        self.cost_report = self.maintenance_cost_to_date

    # thomas_asset = fields.Many2one('thomas.asset', ondelete='cascade')
    # fleet_vehicle = fields.Many2one('fleet.vehicle', ondelete='cascade')
    # name = fields.Char(compute='_compute_vehicle_name', store=True)

    #plate registration?
    unit_no = fields.Char("Unit #", default=default_unit_no, required=True, track_visibility='onchange')
    protractor_workorders = fields.One2many('thomasfleet.workorder', 'vehicle_id', 'Work Orders')
    lease_agreements = fields.One2many('thomaslease.lease','vehicle_id', 'Rental Agreements')
    lease_invoice_ids = fields.Many2many('account.invoice',string='Invoices',
                                   relation='unit_lease_account_invoice_rel')
    lease_agreements_count = fields.Integer(compute='_compute_thomas_counts',string='Rental Agreements Count')
    lease_invoices_count = fields.Integer(compute='_compute_thomas_counts',string='Rental Invoices Count')
    workorder_invoices_count = fields.Integer(compute='_compute_thomas_counts',string='WorkOrders Count')
    unit_slug = fields.Char(compute='_compute_slug', readonly=True)
    vin_id = fields.Char('V.I.N', track_visibility='onchange')
    license_plate = fields.Char('License Plate',  required=False, track_visibility='onchange')
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
    fleet_status = fields.Many2one('fleet.vehicle.state', 'Unit Status', track_visibility='onchange')
    air_conditioning = fields.Selection([('yes', 'Yes'), ('no', 'No')], 'Air Conditioning', default='yes', track_visibility='onchange')
    transmission = fields.Char("Transmission", track_visibility='onchange')
    protractor_guid = fields.Char(compute='protractor_guid_compute', change_default=True)
    stored_protractor_guid = fields.Char(compute='_get_protractor_notes_and_owner', readonly=True)
    qc_check = fields.Boolean('Data Accurracy Validated')
    fin_check = fields.Boolean('Financial Accuracy Validated')
    accessories = fields.One2many('thomasfleet.accessory','vehicle_id',String="Accessories", track_visibility='onchange')
    write_to_protractor = fields.Boolean(default=False)
    production_date = fields.Char("Production Date", track_visibility='onchange')
    pulled_protractor_data = fields.Boolean(default=False,String="Got Data from Protractor")
    protractor_owner_guid = fields.Char(compute='_get_protractor_notes_and_owner', string= 'Protractor Owner ID')
    unit_quality = fields.Selection([('new','New'), ('good','Good'),('satisfactory','Satisfactory'),('poor','Poor')],
                                    'Unit Quality',track_visibility='onchange')

    historical_revenue = fields.Float("Historical Revenue", track_visbility='onchange', default=0.00)
    revenue_to_date = fields.Float("Total Revenue", compute="compute_revenue", readonly=True, store=True)
    total_maintenance_cost_to_date = fields.Float("Lifetime Maintenance Cost", compute="_compute_maintenance_cost",
                                             readonly=True, store=True)
    maintenance_cost_to_date = fields.Float("Reporting Maintenance Cost (from 2020)", compute="_compute_maintenance_cost",
                                             readonly=True, store=True)
    licensing_cost_to_date = fields.Float("Licensing Cost")
    insurance_cost_to_date = fields.Float("Insurance Cost")
    line_items = fields.One2many('account.invoice.line','vehicle_id', String="Invoice Line Items")

    profitability_ratio = fields.Float("Revenue/Cost Ratio", compute="_compute_profitability_ratio", readonly=True,
                                       store=True)
    reporting_profit = fields.Float("Reporting Profit", compute="_compute_profitability_ratio", readonly=True,
                                    store=True)

    lifetime_profit = fields.Float("Total Profit", compute="_compute_profitability_ratio", readonly=True,
                                   store=True)

    all_cost = fields.Float("Total Costs", compute="_compute_maintenance_cost",
                                             readonly=True, store=True)



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

    @api.depends('workorder_invoices_count','protractor_workorders')
    def _compute_maintenance_cost(self):
        wo_rec = self.env['thomasfleet.workorder']
        cu_date = datetime(2021,1,1)
        for rec in self:
            work_orders = wo_rec.search([('vehicle_id', '=', rec.id)])
            for wo in work_orders:
                woDateS = parser.parse(wo.invoiceDate)
                woDate = datetime.strptime(woDateS.strftime('%Y-%m-%d'), '%Y-%m-%d')
                if woDate >= cu_date:
                    rec.maintenance_cost_to_date += wo['netTotal']
                else:
                    rec.total_maintenance_cost_to_date += wo['netTotal']
            rec.all_cost += (rec.total_maintenance_cost_to_date + rec.licensing_cost_to_date + rec.insurance_cost_to_date)


    @api.depends('lease_invoices_count','lease_invoice_ids','historical_revenue')
    def compute_revenue(self):
        for rec in self:
            for line in rec.line_items:
                rec.revenue_to_date += line.price_total
            rec.revenue_to_date += rec.historical_revenue

        #lines = self.env['account.invoice.line']
        #for rec in self:
        #    the_lines = lines.search([('vehicle_id', '=', rec.id)])
        #    for line in the_lines:
        #        rec.revenue_to_date += line.price_total
        #    rec.revenue_to_date = rec.revenue_to_date + rec.historical_revenue

    # accessories = fields.Many2many()
    @api.depends('revenue_to_date', 'maintenance_cost_to_date','total_maintenance_cost_to_date','all_cost' )
    def _compute_profitability_ratio(self):
        for rec in self:
            rec.lifetime_profit = rec.revenue_to_date - rec.all_cost
            rec.reporting_profit = rec.revenue_to_date - rec.maintenance_cost_to_date
            if rec.maintenance_cost_to_date > 0 and rec.revenue_to_date > 0:
                rec.profitability_ratio = rec.revenue_to_date/rec.maintenance_cost_to_date
            else:
                rec.profitability_ratio = 0.0

    @api.depends('stored_protractor_guid')
    def protractor_guid_compute(self):
        #if self:
        #    print('HERE IS THE STORED PGUID:' + str(self.stored_protractor_guid))

        for record in self:
           # print('Computing GUID ' + str(record.stored_protractor_guid))
            if not record.stored_protractor_guid:
                guid = record.get_protractor_id()
                self.log.info("GUID DICTIONARY: " + str(guid))
                #record.stored_protractor_guid = guid['id']
                if guid:
                    #print('Retrieved GUID' + guid['id'])

                    if guid['id']:
                        record.protractor_guid = guid['id']
                        #record.stored_protractor_guid = guid['id']
                        #record.with_context(skip_update=True).stored_protractor_guid = guid['id']
                        #record.with_context(skip_update=True).update({'stored_protractor_guid': guid['id']})
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
        the_workorders = self.with_context(checkDB=True).env['thomasfleet.workorder']
        for record in self:
            record.lease_agreements_count = the_agreements.search_count([('vehicle_id', '=', record.id)])
            record.lease_invoices_count = the_invoices.search_count([('id', 'in', tuple(record.lease_invoice_ids.ids))])
            record.workorder_invoices_count = the_workorders.search_count([('vehicle_id', '=', record.id),
                                                                           ('guid', '=', record.protractor_guid)])


    def ok_pressed(self):
        self.with_context(manual_update=True).update_protractor()

    def check_update_portractor(self):
        theMess = self.env['thomaslease.message']

        rec = theMess.create({'message': "Do you want to unit update " + self.unit_no +" in Protractor?"})

        res = self.env['ir.actions.act_window'].for_xml_id('thomasfleet', 'message_action')

        res.update(
            context=dict(self.env.context, ok_handler='ok_pressed', caller_model=self._name, caller_id=self.id),
            res_id=rec.id
        )
        return res
        # return {
        #
        #     'name': 'Update Protractor',
        #
        #     'type': 'ir.actions.act_window',
        #
        #     'res_model': 'thomaslease.message',
        #
        #     'res_id': rec.id,
        #
        #     'ok_handler': self.ok_pressed,
        #
        #     'view_mode': 'form',
        #
        #     'view_type': 'form',
        #
        #     'target': 'new'
        #
        # }



    def update_protractor(self):
        url = " "
        guid = ""
        if self.stored_protractor_guid:
            url = "https://integration.protractor.com/IntegrationServices/1.0/ServiceItem/"+self.stored_protractor_guid
            guid = self.stored_protractor_guid
        else:
            if self.protractor_guid:
                url = "https://integration.protractor.com/IntegrationServices/1.0/ServiceItem/" + self.protractor_guid
                guid = self.protractor_guid
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
            "ID":guid,
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



    def get_protractor_id(self):
        #print("IN GET PROTRACTOR ID for" + str(self.vin_id))
        self.ensure_one()
        self.log.info("Getting Protarctor ID for Vehicle: "+ str(self.vin_id))
        the_resp = dict()
        the_resp['id']= False
        the_resp['update'] = False
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


            if not the_id:
                the_id = uuid.uuid4()
                the_resp['id']= the_id
                the_resp['update']= True
                self.log.info("Setting Write to protractor cause no id found")
            else:
                self.log.info("Found an existing unit: "+the_id)
                the_resp['id']=the_id
                the_resp['update'] = False
                 #this can only be set on create
        else:
            if self.env.context.get('manual_update'):
                raise models.UserError('Vehicle VIN must be set before it can be linked, created or updated Protractor')

        self.log.info("RETURNING THE RESPONSE " + str(the_resp))
        return the_resp


    @api.multi
    def write(self, values):
        #we only want to update protractor if the unit doesn't exist the firt time
        #subsequent updates shouldn't happen

        self.log.info("IN WRITE FUNCTION for Unit #" + str(self.unit_no))

        record = super(ThomasFleetVehicle,self).write(
            values)

        #self.message_post(body=values)

        self.log.info("Loop Breaker" + str(self.env.context.get('skip_update')))
        if self.env.context.get('skip_update'):
            print("BUSTING OUT")

        else:
            self.log.info("updating protractor")
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

    def getMakeModelTrim(self,make,model,trim):
        theTrim = self.env['thomasfleet.trim'].search(
            [('brand_id.name', '=ilike', make), ('model_id.name', '=ilike', model), ('name', '=ilike', trim)],limit=1)
        return theTrim

    @api.onchange('vin_id')
    #@api.one
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
                #try and find the complete product make,model,trim if not, try to add the missing part
                vehicleMakeModelTrim = self.getMakeModelTrim(themake,themodel,thesubmodel)
                if vehicleMakeModelTrim:
                    self.brand_id = vehicleMakeModelTrim.brand_id
                    self.model_id = vehicleMakeModelTrim.model_id
                    self.trim_id = vehicleMakeModelTrim.id
                else:
                    the_brand = self.env['fleet.vehicle.model.brand'].search([('name', '=ilike', themake)], limit=1)
                    if the_brand:
                        self.brand_id = the_brand.id
                    else:
                        brand_data={'name':themake}
                        the_new_brand = self.env['fleet.vehicle.model.brand'].create(brand_data)
                        self.brand_id = the_new_brand.id

                    the_model = self.env['fleet.vehicle.model'].search([('brand_id', '=', the_brand.id),('name', '=ilike', themodel)],limit=1)
                    if the_model:
                        self.model_id = the_model.id
                    else:
                        model_data={'name': themodel, 'brand_id':self.brand_id.id}
                        the_new_model = self.env['fleet.vehicle.model'].create(model_data)
                        self.model_id = the_new_model.id

                    the_trim = self.env['thomasfleet.trim'].search([('brand_id', '=', the_brand.id),('model_id', '=', the_model.id),('name', '=ilike', thesubmodel)],limit=1)
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

    @api.depends('vin_id')
    #@api.one
    def _get_protractor_notes_and_owner(self):
        the_resp = "NO VIN"
        for record in self:
            if record.vin_id:
                url = "https://integration.protractor.com/IntegrationServices/1.0/ServiceItem/Search/"+record.vin_id
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
                the_id=""

                for item in data['ItemCollection']:
                    the_note = item['Note']
                    the_ownerID = item['OwnerID']
                    the_id = item['ID']

                record.notes = the_note
                record.protractor_owner_guid = the_ownerID
                if not record.stored_protractor_guid:
                    record.stored_protractor_guid = the_id




    def _get_protractor_workorders_tbd(self):
        url = "https://integration.protractor.com/IntegrationServices/1.0/ServiceItem/"+str(self.stored_protractor_guid)+"/Invoice"
        da = datetime.now()
        querystring = {" ": "", "startDate": "2021-11-01", "endDate": da.strftime("%Y-%m-%d"), "%20": ""}

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
        invoices = self.protractor_workorders

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
            invObj = self.env['thomasfleet.workoder'].create(inv)
            invDetsArr = invObj.get_invoice_details_rest()
            inv['workorder_details'] = invDetsArr
            for invoice in invoices:
                if invoice.invoiceNumber == item['InvoiceNumber']:
                    updatedInvoices.append((1, invoice.id, inv))
                    invoiceNotFound = False

            if invoiceNotFound:
                updatedInvoices.append((0,0,inv))



        print("Updated Invoices" + str(updatedInvoices))
        self.update({'protractor_workorders': updatedInvoices})





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
            domain=[('id','in',tuple(self.lease_invoice_ids.ids))]
        )
        print("Unit" + str(self.unit_no))

        return res

    @api.one
    def _get_protractor_workrorders(self):
        print("WORK ORDERS GET")
        print('UNIT # ' + str(self.unit_no))

        wo_rec = self.env['thomasfleet.workorder']

        wo_rec._create_protractor_workorders_for_unit(self.id, self.protractor_guid)

        return

    @api.one
    def _unlink_protractor_workerorders(self):
        wo_rec = self.env['thomasfleet.workorder']
        for rec in self:
            work_orders = wo_rec.search([('vehicle_id', '=', rec.id)])
            for work_order in work_orders:
                print(" DELETING WORKORDER for UNIT "+ str(self.unit_no) +":::" + str(work_order.id))
                work_order.with_context(skip_update=True).unlink()
        return

    @api.one
    def _unlink_journal_items(self):
        ji_rec = self.env['thomasfleet.journal_item']
        for rec in self:
            j_items = ji_rec.search([('vehicle_id', '=', rec.id)])
            for j_item in j_items:
                logging.debug(" DELETING Journal Items for UNIT " + str(self.unit_no) + ":::" + str(j_item.id))
                j_item.with_context(skip_update=True).unlink()
        return

    @api.multi
    def act_get_workorders(self):
        print("WORK ORDERS ACTION")
        print('SELF ID ' + str(self.id))

        wo_rec = self.env['thomasfleet.workorder']
        for rec in self:
            work_orders = wo_rec.search([('vehicle_id', '=', rec.id)])
            for work_order in work_orders:
                print(" DELETING INVOICE:::" + str(work_order.id))
                work_order.unlink()

        #for rec in self:
        #    if rec.protractor_workorders:  # don't add invoices right now if there are some
        #        for inv in rec.protractor_workorders:
        #            print(" DELETING INVOICE:::" + str(inv.invoiceNumber))
        #            inv.unlink()

        wo = self.env['thomasfleet.workorder']
        wos = wo._create_protractor_workorders_for_unit(self.id,self.protractor_guid)
        self.ensure_one()
        res = self.env['ir.actions.act_window'].for_xml_id('thomasfleet', 'thomas_workorder_action')
        res.update(
        context=dict(self.env.context, default_vehicle_id=self.id, search_default_parent_false=True,
                     ),
        domain=[('vehicle_id', '=', self.id)]
        )
        #jitems = self.env['thomasfleet.journal_item']
        #jitems.createJournalItemsForUnit(self.id)

        return res


class ThomasFleetOdometer(models.Model):
    _inherit= 'fleet.vehicle.odometer'
    lease_id = fields.Many2one('thomaslease.lease', 'Rental Agreement')
    customer_id =fields.Many2one(related="lease_id.customer_id", string="Customer", readonly=True)
    activity = fields.Selection([('lease_out', 'Rent Start'), ('lease_in', 'Rent Return'),('service', 'Service'),('spare_swap', 'Spare Swap'), ('spare_swap_back','Spare Swap Back')], string="Activity", track_visibility='onchange')

    def name_get(self):
        if self._context.get('lease'):
            res = []
            for record in self:
                name = '{0:,.2f}'.format(record.value)
                res.append((record.id, name))
            return res
        else:
            print("Context is none")
            return super(ThomasFleetOdometer, self).name_get()

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
    name = fields.Char('Rental Status')
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

class ThomasFleetWorkOrderIndex(models.Model):
    _name = 'thomasfleet.workorder_index'

    invoice_number = fields.Integer("Invoice Number")
    protractor_guid = fields.Char("Protractor GUID")

class ThomasFleetJournalItemWizard(models.TransientModel):
    _name = 'thomasfleet.journal_item.wizard'

    @api.multi
    def delete_all_journal_items(self):
        logging.debug('Deleteing all journal items')
        units = self.env['fleet.vehicle'].search([])
        for unit in units:
            unit._unlink_journal_items()

    @api.multi
    def delete_all_workorders(self):
        logging.debug('Deleting all Work Orders')
        units = self.env['fleet.vehicle'].search([('fleet_status', '!=', 'DISPOSED')])
        for unit in units:
            unit._unlink_protractor_workerorders()

    @api.multi
    def reload_work_orders(self):
        logging.debug('Reloating Work Orders')
        units = self.env['fleet.vehicle'].search([('fleet_status', '!=', 'DISPOSED')])
        wo = self.env['thomasfleet.workorder']
        for un in units:
            if un.vin_id:
                logging.debug("Updating Unit: " + str(un.unit_no) + " : " + str(un.vin_id))
                wo._create_protractor_workorders_for_unit(un.id, un.protractor_guid)
            else:
                logging.debug("NOT UPDATING Unit: " + str(un.unit_no) + " : " + str(un.protractor_guid))

    @api.multi
    def create_all_journal_items(self):
        units = self.env['fleet.vehicle'].search([])
        jitem = self.env['thomasfleet.journal_item']
        for rec in units:
            logging.debug("Adding Journal Items for : " + rec.unit_no)
            jitem.createJournalItemsForUnit(rec.id)



    @api.multi
    def refresh_all_items(self):
        print("Refreshing Items")
        self.delete_all_journal_items()
        self.delete_all_workorders()
        self.reload_work_orders()
        self.create_all_journal_items()




class ThomasFleetJournalItem(models.Model):
    _name = 'thomasfleet.journal_item'

    '''
    def init(self):

        print("INITIALIZING")

        wo_orders = self.env['thomasfleet.workorder'].search([])
        for wo_s in wo_orders:
            print("Deleting Work Orders")
            wo_s.unlink()

        units = self.env['fleet.vehicle'].search([('fleet_status', '!=', 'DISPOSED')])
        wo = self.env['thomasfleet.workorder']
        for unit in units:
            if unit.vin_id:
                print("Updating Unit: " + str(unit.unit_no) + " : " + str(unit.vin_id))
                wo._create_protractor_workorders_for_unit(unit.id, unit.protractor_guid)
                print("Created WorkOrders")
            else:
                print("NOT UPDATING Unit: " + str(unit.unit_no) + " : " + str(unit.protractor_guid))



        jitems = self.env['thomasfleet.journal_item'].search([])
        for jit in jitems:
            jit.unlink()
            print("Deleting")
        iCount = 0



        inv_lines = self.env['account.invoice.line'].search([])
        journal_item = self.env['thomasfleet.journal_item']

        while iCount < 200:
           journal_item.create( {'transaction_date' : inv_lines[iCount].date_invoice,
             'type': 'revenue',
             'revenue':inv_lines[iCount].price_subtotal,
             'invoice_line_id': inv_lines[iCount].id,
             'vehicle_id': inv_lines[iCount].vehicle_id.id,
             'product_id' : inv_lines[iCount].lease_line_id.product_id.id,
             'customer_id': inv_lines[iCount].invoice_id.partner_id.id
            })
           iCount = iCount+1

        iCount = 0
        wo_orders = self.env['thomasfleet.workorder'].search([])

        while iCount < 200:
           journal_item.create({'transaction_date':wo_orders[iCount].invoiceDate,
             'type': 'expense',
             'expense': wo_orders[iCount].netTotal,
             'work_order_id':wo_orders[iCount].id,
             'vehicle_id': wo_orders[iCount].vehicle_id.id,
             'product_id': wo_orders[iCount].product_id.id,
             'customer_id': wo_orders[iCount].customer_id.id
            })
           iCount = iCount+1
    '''


    def createJournalItemsForUnit(self,unit_id):

        inv_lines = self.env['account.invoice.line'].search([('vehicle_id', '=', unit_id),
                                                             ('invoice_id.state', 'not in',['draft', 'cancel']),
                                                             ('invoice_id.thomas_invoice_class', 'in', ['rental','repair'])])
        journal_item = self.env['thomasfleet.journal_item']
        cu_date = datetime(2021, 1, 1)
        for inv in inv_lines:
            woDateS = parser.parse(inv.date_invoice)
            invDate = datetime.strptime(woDateS.strftime('%Y-%m-%d'), '%Y-%m-%d')
            if invDate >= cu_date:
                journal_item.with_context(skip_update=True).create({'transaction_date':inv.date_invoice,
                 'type':'revenue',
                 'revenue':inv.price_subtotal,
                 'invoice_line_id': inv.id,
                 'vehicle_id': inv.vehicle_id.id,
                 'product_id' : inv.lease_line_id.product_id.id,
                 'customer_id': inv.invoice_id.partner_id.id
                })

        wo_orders = self.env['thomasfleet.workorder'].search([('vehicle_id', '=', unit_id)])
        for wo in wo_orders:
            woDateS1 = parser.parse(wo.invoiceDate)
            woDate = datetime.strptime(woDateS1.strftime('%Y-%m-%d'), '%Y-%m-%d')
            if woDate >= cu_date:
                journal_item.with_context(skip_update=True).create({'transaction_date':wo.invoiceDate,
                 'type': 'expense',
                 'expense': wo.rnmTotal,
                 'work_order_id':wo.id,
                 'vehicle_id': wo.vehicle_id.id,
                 'product_id': wo.product_id.id,
                 'customer_id': wo.customer_id.id
                })




    @api.depends('invoice_line_id','work_order_id', 'type')
    def default_vehicle_id(self):
        for rec in self:
            if rec.type == 'revenue':
                return self.invoice_line_id.vehicle_id
            else:
                return self.work_order_id.vehicle_id

    @api.depends('invoice_line_id', 'work_order_id', 'type')
    def default_customer_id(self):
        for rec in self:
            if rec.type == 'revenue':
                return self.invoice_line_id.invoice_id.partner_id
            else:
                return self.work_order_id.customer_id

    @api.depends('invoice_line_id', 'work_order_id', 'type')
    def default_product_id(self):
        for rec in self:
            if rec.type == 'revenue':
                return self.invoice_line_id.lease_line_id.product_id
            else:
                return self.work_order_id.customer_id

    transaction_date = fields.Datetime("Transaction Date")
    expense = fields.Float("Expense")
    revenue = fields.Float("Revenue")
    type = fields.Selection([('revenue', 'Revenue'), ('expense', 'Expense')])
    work_order_id = fields.Many2one('thomasfleet.work_order', string='Work Order', help='Work Order For a Vehicle')
    invoice_line_id = fields.Many2one('account.invoice.line', string='Invoice Line Item', help='Rental Invoice for the Unit')
    customer_id = fields.Many2one('res.partner', deafult=default_customer_id,  string='Customer',
                                  help='Work Order For a Vehicle', readonly=True)
    vehicle_id = fields.Many2one('fleet.vehicle',default=default_vehicle_id,  string='Unit',
                                 help='Work Order For a Vehicle', readonly=True)
    product_id = fields.Many2one('product.product',default=default_product_id, string='Product',
                                 help='Product', readonly=True)


class ThomasFleetWorkOrder(models.Model):
    _name = 'thomasfleet.workorder'
    _res = []
    vehicle_id = fields.Many2one('fleet.vehicle', 'Vehicle')
    customer_id = fields.Many2one('res.partner', 'Customer')
    product_id = fields.Many2one('product.product', 'Product')
    unit_no = fields.Char(related='vehicle_id.unit_no', string="Unit #")
    workorder_details = fields.One2many('thomasfleet.workorder_details', 'workorder_id',  'Work Order Details')
    protractor_guid = fields.Char('Protractor GUID',related='vehicle_id.protractor_guid')
    invoiceTime = fields.Datetime('Invoice Time')
    invoiceDate = fields.Datetime('Invoice Date')
    workOrderTime = fields.Datetime('WorkOrder Time')
    workOrderDate = fields.Datetime('WorkOrder Date')
    technichan = fields.Char('Technician')
    serviceAdvisor = fields.Char('Service Advisor')
    lastModifiedBy = fields.Char('Last Modified By')
    workOrderNumber = fields.Char('Work Order Number')
    workflowStage = fields.Char("Workflow Stage")
    invoiceNumber = fields.Char('Invoice Number')
    partsTotal = fields.Float('Parts Total')
    subletTotal= fields.Float('Sublet Total')
    grandTotal=fields.Float('Grand Total')
    laborTotal=fields.Float('Labor Total')
    otherChargeTotal = fields.Float('Other Charge Total')
    netTotal=fields.Float('Net Total')
    rnmTotal = fields.Float('RnM Total', compute="_compute_rnm_total")
    invoice_guid = fields.Char('Invoice Guid')



    '''
    def read(self, fields = None, load = '_classic_read' ):
        print("Read")
        #wo_index_rec = self.env['thomasfleet.workorder_index']
        #theID = arg[0]
        #index = wo_index_rec.search([('invoice_number', '=', theID)], limit=1)
       # print("The Invoice GUID " + str(index.protractor_guid))
        # mod = super(ThomasFleetWorkOrder, self).read(fields, load)
        self.protractor_guid = "abc"
        return [self]

    def browse(self, arg=None, prefetch=None):
        print("Browse")
        wo_index_rec = self.env['thomasfleet.workorder_index']
        theID = arg[0]
        index = wo_index_rec.search([('invoice_number', '=', theID)],limit=1)
        print("The Invoice GUID " + str(index.protractor_guid))
        #mod = super(ThomasFleetWorkOrder, self).read(fields, load)
        return 
        
          return {'id': self.id, 'invoice_guid': str(index.protractor_guid), 'invoiceTime': '',
                 'invoiceDate': '', 'workOrderTime': '', 'workOrderDate': '', 'technichan': 'Me',
                 'serviceAdvisor': 'You', 'lastModifiedBy': '',
                 'workOrderNumber': 'FB', 'workflowStage': 'FUB', 'invoiceNumber': 'ABCD', 'partsTotal': 1.00,
                 'subletTotal': 1.00, 'grandTotal': 1.00,
                 'laborTotal': 1.00, 'netTotal': 2.00}
   
     return [{'id': theID, 'invoice_guid': str(index.protractor_guid),'invoiceTime':'',
    'invoiceDate':'', 'workOrderTime':'','workOrderDate':'','technichan':'Me','serviceAdvisor':'You','lastModifiedBy':'',
    'workOrderNumber':'FB','workflowStage':'FUB','invoiceNumber':'ABCD','partsTotal':1.00, 'subletTotal':1.00, 'grandTotal':1.00,
    'laborTotal':1.00,'netTotal':2.00}]

    def search_count(self, args):
        print("Search Count")
        if len(args) == 1:
            return super(ThomasFleetWorkOrder, self.with_context(checkDB=True)).search_count(args)
        else:
            if len(args) == 2:
                guid = args[1][2]
                wos = self._get_protractor_workorders_for_unit(guid)
            else:
                wos = self._get_protractor_workorders()
            return len(wos)
'''
    '''
    @api.model
    def search(self, args, offset=0, limit=None, order=None, count=False):
        print("Search")
        if self._context.get('loadFromProtractor'):
            guid = args[1][2]
            wos = self._get_protractor_workorders_for_unit(guid)
        else:
            wos = super(ThomasFleetWorkOrder, self).search(args,offset,limit,order,count)
        return wos
 
        if len(args) == 3:
            return super(ThomasFleetWorkOrder, self.with_context(checkDB=True)).search(args,offset,limit,order,count)
        else:
            if len(args) == 2:
                guid = args[1][2]
                wos = self._get_protractor_workorders_for_unit(guid)
            else:
                wos = self._get_protractor_workorders()
            if offset > 0:
               return wos[offset:(offset + limit)]
            else:
               return wos  # [{'id':'test','invoiceDate':'test'}]
        '''

    '''
    @api.model
    def search_read(self, domain=None, fields=None, offset=0, limit=None, order=None):
        print("Search Read")
        if self._context.get('loadFromProtractor'):
            guid = domain[1][2]
            wos = self._get_protractor_workorders_for_unit(guid)
        else:
            wos = super(ThomasFleetWorkOrder, self).searc_read(domain, fields, offset, limit, order)
        return wos
   
        if len(domain) == 3:
            return super(ThomasFleetWorkOrder, self.with_context(checkDB=True)).search_read(domain,fields,offset,limit,order)
        else:
            if len(domain) == 2:
                guid = domain[1][2]
                wos = self._get_protractor_workorders_for_unit(guid)
            else:
                wos = self._get_protractor_workorders()
            if offset > 0:
                return wos[offset:(offset+limit)]
            else:
                return wos  # [{'id':'test','invoiceDate':'test'}]
    '''
    def _compute_rnm_total(self):
        for rec in self:
            rec.rnmTotal = rec.netTotal + rec.otherChargeTotal

    def search_count(self, args):
        print("Search Count")
        if len(args) == 1:
            return super(ThomasFleetWorkOrder, self).search_count(args)
        else:
            if len(args) == 2:
                vehicle_id = args[0][2]
                guid = args[1][2]
                wos = self._get_protractor_workorders_for_unit(vehicle_id,guid)
            else:
                wos = self._get_protractor_workorders()
            return len(wos)

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
        for invDets in self.workorder_details:
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

            inv_detail['workorder_line_items'] = sp_lines

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
        for invDets in self.workorder_details:
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

            inv_detail['workorder_line_items']= sp_lines
            self.workorder_details = [(0, 0, inv_detail)]


            #inv_det_model.create(inv_detail)
            #i_details = []
            #i_details.append((0,0,the_details))


            #self.update({'invoice_details': inv_detail})

        # @api.one


    def thomas_workorder_form_action(self):
        print("THOMAS FORM ACTION")

    def _create_protractor_workorders_for_all_units(self):
        units = self.env['fleet.vehicle'].search([('fleet_status', '!=', 'DISPOSED')])
        self.log.info("Number of Units for Updating: " + str(len(units)))
        for unit in units:
            if unit.vin_id:
                self.log.info("Updating Unit: " + str(unit.unit_no) + " : " + str(unit.vin_id))
                self._create_protractor_workorders_for_unit(unit.id, unit.protractor_guid)
                self.log.info("Created WorkOrders")
            else:
                print("NOT UPDATING Unit: " + str(unit.unit_no) + " : " + str(unit.protractor_guid))

    def _create_protractor_workorders_for_unit(self,vehicle_id,unit_guid):
        url = "https://integration.protractor.com/IntegrationServices/1.0/ServiceItem/" + str(
            unit_guid) + "/Invoice"
        da = datetime.now()
        querystring = {" ": "", "startDate": "2021-01-01", "endDate": da.strftime("%Y-%m-%d"), "%20": ""}

        headers = {
            'connectionId': "8c3d682f873644deb31284b9f764e38f",
            'apiKey': "fb3c8305df2a4bd796add61e646f461c",
            'authentication': "S2LZy0munq81s/uiCSGfCvGJZEo=",
            'Accept': "application/json",
            'cache-control': "no-cache",
            'Postman-Token': "7c083a2f-d5ce-4c1a-aa35-8da253b61bee"
        }

        response = requests.request("GET", url, headers=headers, params=querystring)
        # print("INVOICE DATA " + response.text)
        workorders = []
        the_unit = self.env['fleet.vehicle'].search([('id','=',vehicle_id)])
        if response.status_code == 200:
            data = response.json()
            aid = 0
            for item in data['ItemCollection']:
                # if item['ID'] not in workorders.items():
                #    print("Not Found")
                aid = aid + 1
                inv = {'vehicle_id': vehicle_id,
                       'unit_no' : the_unit.unit_no,
                       'invoice_guid': item['ID'],
                       'workOrderNumber': str(item['WorkOrderNumber']),
                       'workflowStage': item['WorkflowStage'],
                       'invoiceNumber': str(item['InvoiceNumber'])}
                if 'Summary' in item:
                    inv['grandTotal'] = item['Summary']['GrandTotal']
                    inv['netTotal'] = item['Summary']['NetTotal']
                    inv['laborTotal'] = item['Summary']['LaborTotal']
                    inv['partsTotal'] = item['Summary']['PartsTotal']
                    inv['subletTotal'] = item['Summary']['SubletTotal']
                    inv['otherChargeTotal']= item['Summary']['OtherChargeTotal']
                woStr = str(item['Header']['CreationTime'])
                wod = parser.parse(woStr)
                # woDT = str(item['Header']['CreationTime']).split("T")
                # woDT = datetime(item['Header']['CreationTime'])s
                wdate = datetime.strptime(wod.strftime('%Y-%m-%d'), '%Y-%m-%d')
                inv['workOrderDate'] = wod.date()
                #inv['workOrderTime'] = wod.time()
                invStr = str(item['InvoiceTime'])
                invDT = parser.parse(invStr)  # str(item['InvoiceTime']).split("T")
                iDate = datetime.strptime(invDT.strftime('%Y-%m-%d'), '%Y-%m-%d')
                inv['invoiceDate'] = invDT.date()
                #inv['invoiceTime'] = iDate.time()
                if 'Technician' in item:
                    inv['technichan'] = str(item['Technician']['Name'])
                if 'ServiceAdvisor' in item:
                    inv['serviceAdvisor'] = str(item['ServiceAdvisor']['Name'])
                if 'Header' in item:
                    per = str(item['Header']['LastModifiedBy'])
                    uName = per.split("\\")
                    # print(uName)
                    inv['lastModifiedBy'] = uName[1]
                if 'Contact' in item:
                    con_guid = item['Contact']['ID']
                    if con_guid:
                        customer_id = self.env['res.partner'].search([('protractor_guid', '=', con_guid)])
                        if customer_id:
                            print("Found Customer ID: " + str(customer_id) + " for: "+con_guid)
                            inv['customer_id'] = customer_id.id
                        else:
                            inv['customer_id'] = False

                product_id = self.env['product.product'].search([('name', 'like','Maintenance - General')])
                if product_id:
                    inv['product_id'] = product_id.id
                else:
                    inv['product_id'] = False
                dbINV = self.with_context(skip_update=True).create(inv)
                print("WorkOrder Created -> ID " + str(dbINV.id))
                workorders.append(dbINV)

        return workorders

    def _get_protractor_workorders_for_unit(self,vehicle_id,unit_guid):
        url = "https://integration.protractor.com/IntegrationServices/1.0/ServiceItem/" + str(
            unit_guid) + "/Invoice"
        da = datetime.now()
        querystring = {" ": "", "startDate": "2021-01-01", "endDate": da.strftime("%Y-%m-%d"), "%20": ""}

        headers = {
            'connectionId': "8c3d682f873644deb31284b9f764e38f",
            'apiKey': "fb3c8305df2a4bd796add61e646f461c",
            'authentication': "S2LZy0munq81s/uiCSGfCvGJZEo=",
            'Accept': "application/json",
            'cache-control': "no-cache",
            'Postman-Token': "7c083a2f-d5ce-4c1a-aa35-8da253b61bee"
        }

        response = requests.request("GET", url, headers=headers, params=querystring)
        workorders = []
        #print("INVOICE DATA " + response.text)
        if response.status_code == 200:
            data = response.json()
            aid = 0
            for item in data['ItemCollection']:
                # if item['ID'] not in workorders.items():
                #    print("Not Found")
                aid = aid + 1
                inv = {'vehicle_id': vehicle_id,
                       'invoice_guid': item['ID'],
                       'workOrderNumber': str(item['WorkOrderNumber']),
                       'workflowStage': item['WorkflowStage'],
                       'invoiceNumber': str(item['InvoiceNumber'])}
                if 'Summary' in item:
                    inv['grandTotal'] = item['Summary']['GrandTotal']
                    inv['netTotal'] = item['Summary']['NetTotal']
                    inv['laborTotal'] = item['Summary']['LaborTotal']
                    inv['partsTotal'] = item['Summary']['PartsTotal']
                    inv['subletTotal'] = item['Summary']['SubletTotal']
                    inv['otherChargeTotal'] = item['Summary']['OtherChargeTotal']
                woStr=str(item['Header']['CreationTime'])
                wod = parser.parse(woStr)
                #woDT = str(item['Header']['CreationTime']).split("T")
                #woDT = datetime(item['Header']['CreationTime'])s
                wdate = datetime.strptime(wod.strftime('%Y-%m-%d'),'%Y-%m-%d')
                inv['workOrderDate'] = wdate.date()
                inv['workOrderTime'] = wdate.time()
                invStr = str(item['InvoiceTime'])
                invDT = parser.parse(invStr)#str(item['InvoiceTime']).split("T")
                iDate = datetime.strptime(invDT.strftime('%Y-%m-%d'),'%Y-%m-%d')
                inv['invoiceDate'] = iDate.date()
                inv['invoiceTime'] = iDate.time()
                if 'Technician' in item:
                    inv['technichan'] = str(item['Technician']['Name'])
                if 'ServiceAdvisor' in item:
                    inv['serviceAdvisor'] = str(item['ServiceAdvisor']['Name'])
                if 'Header' in item:
                    per = str(item['Header']['LastModifiedBy'])
                    uName = per.split("\\")
                    # print(uName)
                    inv['lastModifiedBy'] = uName[1]
                if 'Contact' in item:
                    con_guid = item['Contact']['ID']
                    if con_guid:
                        customer_id = self.env['res.partner'].search([('protractor_guid', '=', con_guid)])
                        if customer_id:
                            print("Found Customer ID: " + str(customer_id) + " for: "+con_guid)
                            inv['customer_id'] = [(4,customer_id)]
                        else:
                            inv['customer_id'] = []
                #dbINV = self.create(inv)
                workorders.append(inv)

        return workorders

    def _get_protractor_workorders(self):
        url = "https://integration.protractor.com/IntegrationServices/1.0/WorkOrder/"
        da = datetime.now()
        querystring = {" ": "", "startDate": "2021-01-01", "endDate": da.strftime("%Y-%m-%d"), "%20": ""}#, "readInProgress":"True"}

        headers = {
            'connectionId': "8c3d682f873644deb31284b9f764e38f",
            'apiKey': "fb3c8305df2a4bd796add61e646f461c",
            'authentication': "S2LZy0munq81s/uiCSGfCvGJZEo=",
            'Accept': "application/json",
            'cache-control': "no-cache",
            'Postman-Token': "7c083a2f-d5ce-4c1a-aa35-8da253b61bee"
        }

        response = requests.request("GET", url, headers=headers, params=querystring)
        print("WORK ORDER DATA " + response.text)
        data = response.json()

        workorders = [] #self._res
        aid = 0
        for item in data['ItemCollection']:
            #if item['ID'] not in workorders.items():
            #    print("Not Found")
            aid = aid +1
            inv={'id':item['InvoiceNumber'],'vehicle_id': self.id,
                 'invoice_guid' : item['ID'],
                 'workOrderNumber': item['WorkOrderNumber'],
                 'workflowStage' : item['WorkflowStage'],
                 'invoiceNumber': item['InvoiceNumber']}
            if 'Summary' in item:
                inv['grandTotal'] = item['Summary']['GrandTotal']
                inv['netTotal'] = item['Summary']['NetTotal']
                inv['laborTotal'] = item['Summary']['LaborTotal']
                inv['partsTotal'] = item['Summary']['PartsTotal']
                inv['subletTotal'] = item['Summary']['SubletTotal']
                inv['otherChargeTotal'] = item['Summary']['OtherChargeTotal']

            woDT = str(item['Header']['CreationTime']).split("T")
            inv['workOrderDate'] = woDT[0]
            inv['workOrderTime'] = woDT[1]
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
            if 'Contact' in item:
                con_guid = item['Contact']['ID']
                if con_guid:
                    customer_id = self.env['res.partner'].search([('protractor_guid', '=', con_guid)])
                    if customer_id:
                        print("Found Customer ID: " + str(customer_id) + " for: " + con_guid)
                        inv['customer_id'] = customer_id.id
                    else:
                        inv['customer_id'] = False

            product_id = self.env['product.product'].search([('name', 'like','Maintenance - General')])
            if product_id:
                inv['product_id'] = product_id.id
            else:
                inv['product_id'] = False

            workorders.append(inv)

        return workorders

    @api.multi
    def act_get_workorder_details(self):
        print("FIRED OF INVOICE DETAILS ACTION")
        for rec in self:
            if rec.workorder_details:  # don't add invoices right now if there are some
                for inv_det in rec.invoice_details:
                    print("UNLINKING  INVOICE:::" + str(inv_det.workorder_id))
                    inv_det.unlink()
        self.ensure_one()
        self.get_workorder_details()

        res = self.env['ir.actions.act_window'].for_xml_id('thomasfleet', 'thomas_workorder_details_action')
        res.update(
            context=dict(self.env.context, default_workorder_id=self.id, search_default_parent_false=True),
            domain=[('workorder_id', '=', self.id)]
        )
        return res

    @api.multi
    def generate_account_invoices(self):
        print ("Generating Account Invoices")


class ThomasFleetWorkOrderDetails(models.Model):
    _name = 'thomasfleet.workorder_details'
    workorder_id = fields.Many2one('thomasfleet.workorder', 'Work Order')
    workorder_line_items = fields.One2many('thomasfleet.workorder_details_line', 'workorder_details_id', 'Work Order Details Line')
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

        res = self.env['ir.actions.act_window'].for_xml_id('thomasfleet', 'thomas_workorder_details_line_action')
        res.update(
            context=dict(self.env.context, default_invoice_id = self.id, search_default_parent_false=True),
            domain=[('workorder_details_id', '=', self.id)]
         )
        return res



class ThomasFleetWorkOrderDetailsLine(models.Model):
    _name = 'thomasfleet.workorder_details_line'
    workorder_details_id = fields.Many2one('thomasfleet.workorder_details', 'WorkOrder Details')
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

    # def search(self, args, offset=0, limit=None, order=None, count=False):
    #     return  super(ThomasFleetAccessoryType,self).search(args,offset,limit,order,count)
    #
    # def search_read(self, domain=None, fields=None, offset=0, limit=None, order=None):
    #
    #     return super(ThomasFleetAccessoryType, self).search_read( domain, fields, offset, limit, order)

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
                    if record.name and record.unit_no:
                        name = record.name + " " + record.unit_no
                    else:
                        name = " 407 Transponder"
                    res.append((record.id, name))
                else:
                    res.append((record.id,record.name))
            return res



class ThomasFleetMXInvoiceWizard(models.TransientModel):
    _name = 'thomasfleet.mx.invoice.wizard'
    lease_ids = fields.Many2many('thomaslease.lease', string="Rent")
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