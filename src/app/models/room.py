"""Room, RoomType and Equipment tables."""
from ..extensions import db

room_equipment = db.Table(
    "room_equipment",
    db.Column("room_id", db.Integer, db.ForeignKey("rooms.id"), primary_key=True),
    db.Column("equipment_id", db.Integer, db.ForeignKey("equipment.id"), primary_key=True),
)


class RoomType(db.Model):
    """What kind of room it is: lecture hall, lab, classroom, meeting room..."""

    __tablename__ = "room_types"

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(50), unique=True, nullable=False)
    description = db.Column(db.String(255))

    def to_dict(self):
        return {"id": self.id, "name": self.name, "description": self.description}


class Equipment(db.Model):
    """Something a room can have: projector, computers, whiteboard..."""

    __tablename__ = "equipment"

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(50), unique=True, nullable=False)

    def to_dict(self):
        return {"id": self.id, "name": self.name}


class Room(db.Model):
    __tablename__ = "rooms"

    id = db.Column(db.Integer, primary_key=True)
    code = db.Column(db.String(20), unique=True, nullable=False)  # e.g. "B-204"
    name = db.Column(db.String(100))
    building = db.Column(db.String(50), nullable=False)
    floor = db.Column(db.Integer)
    capacity = db.Column(db.Integer, nullable=False)
    room_type_id = db.Column(db.Integer, db.ForeignKey("room_types.id"), nullable=False)
    # Rooms are deactivated, not deleted, so old bookings still point somewhere.
    is_active = db.Column(db.Boolean, nullable=False, default=True)

    room_type = db.relationship("RoomType")
    equipment = db.relationship("Equipment", secondary=room_equipment, order_by="Equipment.name")

    def to_dict(self):
        return {
            "id": self.id,
            "code": self.code,
            "name": self.name,
            "building": self.building,
            "floor": self.floor,
            "capacity": self.capacity,
            "room_type": self.room_type.name if self.room_type else None,
            "equipment": [item.name for item in self.equipment],
            "is_active": self.is_active,
        }
