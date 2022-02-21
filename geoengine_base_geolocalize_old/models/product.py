import logging

from odoo import api, exceptions, fields, models
from odoo.tools.translate import _
from collections import defaultdict
#from odoo import geopandas as gp



try:
    import requests
except ImportError:
    logger = logging.getLogger(__name__)
    logger.warning("requests is not available in the sys path")

_logger = logging.getLogger(__name__)

class product(models.Model):
    _inherit = 'product.template'
    _description = 'Description'

    def geocode_address(self):
        """Get the latitude and longitude by requesting the "Nominatim"
        search engine from "openstreetmap". See:
        https://nominatim.org/release-docs/latest/api/Overview/
        """
        url = "http://nominatim.openstreetmap.org/search"
        headers = {"User-Agent": "Odoobot/13.0.1.0.0 (OCA-geospatial)"}

        for partner in self:
            pay_load = {
                "limit": 1,
                "format": "json",
                "street": partner.street or "",
                "postalCode": partner.zip or "",
                "city": partner.city or "",
                "state": partner.state_id and partner.state_id.name or "",
                "country": partner.country_id and partner.country_id.name or "",
                "countryCodes": partner.country_id and partner.country_id.code or "",
            }

            request_result = requests.get(url, params=pay_load, headers=headers)
            try:
                request_result.raise_for_status()
            except Exception as e:
                _logger.exception("Geocoding error")
                raise exceptions.UserError(_("Geocoding error. \n %s") % str(e))
            vals = request_result.json()
            vals = vals and vals[0] or {}
            partner.write(
                {
                    "partner_latitude": vals.get("lat"),
                    "partner_longitude": vals.get("lon"),
                    "date_localization": fields.Date.today(),
                }
            )

    def geo_localize(self):
        self.geocode_address()
        return True

    @api.depends("partner_latitude", "partner_longitude")
    def _compute_geo_point(self):
        """
        Set the `geo_point` of the partner depending of its `partner_latitude`
        and its `partner_longitude`
        **Notes**
        If one of those parameters is not set then reset the partner's
        geo_point and do not recompute it
        """
        for partner in self:
            if not partner.partner_latitude or not partner.partner_longitude:
                partner.geo_point = False
            else:
                partner.geo_point = fields.GeoPoint.from_latlon(
                    partner.env.cr, partner.partner_latitude, partner.partner_longitude
                )

    partner_latitude = fields.Float(string='Geo Latitude', digits=(16, 5))
    partner_longitude = fields.Float(string='Geo Longitude', digits=(16, 5))
    geo_point = fields.GeoPoint(string="point")
    geo_multiLine = fields.GeoMultiLine(string="multiline")
    geo_polygon = fields.GeoPolygon(string="polygon")
    geo_multi_polygon = fields.GeoMultiPolygon(string="multi polygon")
    date_localization = fields.Date(string="Date Localization")

    street = fields.Char(string='street')
    street2 = fields.Char(string="street2")
    zip = fields.Char(string="zip",change_default=True)
    city = fields.Char(string="city")
    state_id = fields.Many2one("res.country.state", string='State', ondelete='restrict', domain="[('country_id', '=?', country_id)]")
    country_id = fields.Many2one('res.country', string='Country', ondelete='restrict')
    contact_address_complete = fields.Char(compute='_compute_complete_address', store=True)
    marker_color = fields.Char(
        string='Marker Color', default='red', required=True)

#    def get_point(self):
#        df1 = self.geo_multi_polygon
#        gdf = gp.GeoDataFrame(df1, geometry= gp.points_from_xy(df1.longitude, df1.latitude))
#        print(gdf['geometry'])

    @api.model
    def update_latitude_longitude(self, partners):
        partners_data = defaultdict(list)

        for partner in partners:
            if 'id' in partner and 'partner_latitude' in partner and 'partner_longitude' in partner:
                partners_data[(partner['partner_latitude'], partner['partner_longitude'])].append(partner['id'])

        for values, partner_ids in partners_data.items():
            # NOTE this should be done in sudo to avoid crashing as soon as the view is used
            self.browse(partner_ids).sudo().write({
                'partner_latitude': values[0],
                'partner_longitude': values[1],
            })

        return {}

    @api.onchange('street', 'zip', 'city', 'state_id', 'country_id')
    def _delete_coordinates(self):
        self.partner_latitude = False
        self.partner_longitude = False

    @api.depends('street', 'zip', 'city', 'country_id')
    def _compute_complete_address(self):
        for record in self:
            record.contact_address_complete = ''
            if record.street:
                record.contact_address_complete += record.street+','
            if record.zip:
                record.contact_address_complete += record.zip+ ' '
            if record.city:
                record.contact_address_complete += record.city+','
            if record.country_id:
                record.contact_address_complete += record.country_id.name

