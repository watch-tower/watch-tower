from app import db


class Inventory(db.Model):
    __tablename__ = "Inventory"
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String)

    def __repr__(self):
        return '<Inventory %s>' % self.name

class Host(db.Model):
    __tablename__ = "Host"
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String)
    inventory_id = db.Column(db.Integer, db.ForeignKey('Inventory.id'), name="fk_inventory")

    def __repr__(self):
        return '<Host %s>' % self.name

class Variable(db.Model):
    __tablename__ = "Variable"
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String)
    value = db.Column(db.String)
    host_id = db.Column(db.Integer, db.ForeignKey('Host.id'), name="fk_host")

    def __repr__(self):
        return '<Variable %s=%s>' % (self.name, self.value)

