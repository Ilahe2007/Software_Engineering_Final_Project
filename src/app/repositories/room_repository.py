"""All database access for rooms, room types and equipment."""
from sqlalchemy import func

from ..extensions import db
from ..models import Equipment, Room, RoomType


class RoomRepository:
    def list_rooms(self, building=None, min_capacity=None, room_type=None,
                   equipment=None, include_inactive=False):
        query = db.select(Room).order_by(Room.building, Room.code)
        if not include_inactive:
            query = query.where(Room.is_active.is_(True))
        # Text filters ignore upper/lower case: building=b finds building "B".
        if building:
            query = query.where(func.lower(Room.building) == building.lower())
        if min_capacity is not None:
            query = query.where(Room.capacity >= min_capacity)
        if room_type:
            query = query.join(Room.room_type).where(func.lower(RoomType.name) == room_type.lower())
        # The room must have every piece of equipment asked for, not just one.
        for name in equipment or []:
            query = query.where(Room.equipment.any(func.lower(Equipment.name) == name.lower()))
        return list(db.session.scalars(query))

    def get(self, room_id):
        return db.session.get(Room, room_id)

    def get_by_code(self, code):
        return db.session.scalar(db.select(Room).where(Room.code == code))

    def add(self, room):
        db.session.add(room)
        db.session.commit()
        return room

    def save(self):
        db.session.commit()

    def list_room_types(self):
        return list(db.session.scalars(db.select(RoomType).order_by(RoomType.name)))

    def get_room_type_by_name(self, name):
        return db.session.scalar(db.select(RoomType).where(RoomType.name == name))

    def add_room_type(self, name, description=None):
        room_type = RoomType(name=name, description=description)
        db.session.add(room_type)
        db.session.commit()
        return room_type

    def get_room_type(self, room_type_id):
        return db.session.get(RoomType, room_type_id)

    def count_rooms_with_type(self, room_type_id):
        query = db.select(func.count()).select_from(Room).where(Room.room_type_id == room_type_id)
        return db.session.scalar(query)

    def get_equipment(self, equipment_id):
        return db.session.get(Equipment, equipment_id)

    def count_rooms_with_equipment(self, equipment_id):
        query = db.select(func.count()).select_from(Room).where(Room.equipment.any(Equipment.id == equipment_id))
        return db.session.scalar(query)

    def delete(self, item):
        db.session.delete(item)
        db.session.commit()

    def list_equipment(self):
        return list(db.session.scalars(db.select(Equipment).order_by(Equipment.name)))

    def get_equipment_by_names(self, names):
        if not names:
            return []
        return list(db.session.scalars(db.select(Equipment).where(Equipment.name.in_(names))))

    def add_equipment(self, name):
        item = Equipment(name=name)
        db.session.add(item)
        db.session.commit()
        return item
