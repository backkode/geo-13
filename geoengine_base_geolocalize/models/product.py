from odoo import fields, models, api


class product(models.Model):
    _name = 'product.product'
    _description = 'Description'

    geo_point = fields.GeoPoint(readonly=False, store=True)
    geo_multiLine = fields.GeoMultiLine(readonly=False, store=True)
    geo_polygon = fields.GeoPolygon(readonly=False, store=True)
    geo_multi_polygon = fields.GeoMultiPolygon(readonly=False, store=True)
