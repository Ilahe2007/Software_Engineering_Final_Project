"""Book a free room, list my bookings, cancel a booking."""
from flask import current_app, jsonify, request

from ..auth.decorators import current_user, login_required
from . import bp
from .service import BookingService
from .validators import parse_status_filter, validate_booking_payload


def _service():
    config = current_app.config
    return BookingService(config["OPENING_HOUR"], config["CLOSING_HOUR"])


@bp.post("/bookings")
@login_required
def create_booking():
    """Book a room for an event.
    ---
    tags: [Bookings]
    security: [{Bearer: []}]
    parameters:
      - in: body
        name: body
        required: true
        schema:
          type: object
          required: [room_id, title, start, end, attendees]
          example: {room_id: 1, title: "Robotics club meeting", start: "2026-12-01T10:00", end: "2026-12-01T12:00", attendees: 20, room_type: "lab", equipment: ["projector"]}
    responses:
      201: {description: Booking confirmed.}
      400: {description: "Invalid data, or the room does not fit: time range, capacity, room type, equipment."}
      401: {description: Not logged in.}
      404: {description: No room with this id.}
      409: {description: The room is already booked at that time.}
    """
    data = validate_booking_payload(request.get_json(silent=True))
    booking = _service().create(current_user(), data)
    return jsonify(booking.to_dict()), 201


@bp.get("/bookings/me")
@login_required
def my_bookings():
    """My bookings, soonest first.
    ---
    tags: [Bookings]
    security: [{Bearer: []}]
    parameters:
      - {name: status, in: query, type: string, enum: [confirmed, cancelled]}
    responses:
      200: {description: The logged-in user's bookings.}
      400: {description: Unknown status.}
      401: {description: Not logged in.}
    """
    status = parse_status_filter(request.args)
    result = _service().list_for_user(current_user(), status)
    return jsonify(count=len(result), bookings=[booking.to_dict() for booking in result])


@bp.delete("/bookings/<int:booking_id>")
@login_required
def cancel_booking(booking_id):
    """Cancel one of my bookings (admins can cancel any). The booking is kept with status "cancelled".
    ---
    tags: [Bookings]
    security: [{Bearer: []}]
    parameters:
      - {name: booking_id, in: path, type: integer, required: true}
    responses:
      200: {description: Booking cancelled.}
      401: {description: Not logged in.}
      404: {description: No such booking among the ones you may see.}
      409: {description: Already cancelled, or it has already started.}
    """
    booking = _service().cancel(current_user(), booking_id)
    return jsonify(booking.to_dict())
