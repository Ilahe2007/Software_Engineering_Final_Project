def codes(response):
    return [room["code"] for room in response.get_json()["rooms"]]


def test_list_all_rooms(client, seeded):
    response = client.get("/api/v1/rooms")
    assert response.status_code == 200
    assert codes(response) == ["A-101", "B-204", "B-205"]


def test_filter_by_building_and_capacity(client, seeded):
    assert codes(client.get("/api/v1/rooms?building=B")) == ["B-204", "B-205"]
    assert codes(client.get("/api/v1/rooms?min_capacity=28")) == ["A-101", "B-204"]


def test_filter_by_type(client, seeded):
    assert codes(client.get("/api/v1/rooms?room_type=lab")) == ["B-204", "B-205"]


def test_equipment_filter_needs_all_items(client, seeded):
    assert codes(client.get("/api/v1/rooms?equipment=projector")) == ["A-101", "B-204"]
    assert codes(client.get("/api/v1/rooms?equipment=projector,computers")) == ["B-204"]


def test_bad_capacity_filter(client, seeded):
    response = client.get("/api/v1/rooms?min_capacity=many")
    assert response.status_code == 400
    assert "min_capacity" in response.get_json()["details"]


def test_get_one_room(client, seeded):
    response = client.get(f"/api/v1/rooms/{seeded['B-204']}")
    assert response.status_code == 200
    assert response.get_json()["equipment"] == ["computers", "projector"]


def test_get_missing_room(client, seeded):
    assert client.get("/api/v1/rooms/9999").status_code == 404


def test_create_room_needs_admin(client, seeded, student_headers):
    body = {"code": "C-1", "building": "C", "capacity": 10, "room_type": "lab"}
    assert client.post("/api/v1/rooms", json=body).status_code == 401
    assert client.post("/api/v1/rooms", json=body, headers=student_headers).status_code == 403


def test_create_room_reports_every_error(client, admin_headers, seeded):
    response = client.post("/api/v1/rooms", json={"capacity": 0, "color": "red"}, headers=admin_headers)
    assert response.status_code == 400
    details = response.get_json()["details"]
    assert set(details) == {"capacity", "code", "building", "room_type", "unknown_fields"}


def test_create_room_with_unknown_type_or_equipment(client, admin_headers, seeded):
    body = {"code": "C-1", "building": "C", "capacity": 10, "room_type": "kitchen"}
    assert "room_type" in client.post("/api/v1/rooms", json=body, headers=admin_headers).get_json()["details"]

    body = {"code": "C-1", "building": "C", "capacity": 10, "room_type": "lab", "equipment": ["laser"]}
    assert "equipment" in client.post("/api/v1/rooms", json=body, headers=admin_headers).get_json()["details"]


def test_duplicate_room_code(client, admin_headers, seeded):
    body = {"code": "A-101", "building": "A", "capacity": 10, "room_type": "lab"}
    assert client.post("/api/v1/rooms", json=body, headers=admin_headers).status_code == 409


def test_update_room(client, admin_headers, seeded):
    room_id = seeded["B-205"]
    response = client.patch(
        f"/api/v1/rooms/{room_id}",
        json={"capacity": 40, "equipment": ["projector", "whiteboard"]},
        headers=admin_headers,
    )
    assert response.status_code == 200
    data = response.get_json()
    assert data["capacity"] == 40
    assert data["equipment"] == ["projector", "whiteboard"]
    assert data["code"] == "B-205"


def test_update_to_existing_code_is_refused(client, admin_headers, seeded):
    response = client.patch(f"/api/v1/rooms/{seeded['B-205']}", json={"code": "B-204"}, headers=admin_headers)
    assert response.status_code == 409


def test_deactivated_room_is_hidden_from_list(client, admin_headers, seeded):
    response = client.delete(f"/api/v1/rooms/{seeded['A-101']}", headers=admin_headers)
    assert response.status_code == 200
    assert response.get_json()["is_active"] is False
    assert "A-101" not in codes(client.get("/api/v1/rooms"))


def test_room_types_and_equipment(client, admin_headers, seeded):
    assert [t["name"] for t in client.get("/api/v1/room-types").get_json()] == ["lab", "lecture_hall"]
    assert client.post("/api/v1/room-types", json={"name": "lab"}, headers=admin_headers).status_code == 409
    assert client.post("/api/v1/equipment", json={"name": ""}, headers=admin_headers).status_code == 400


def test_filters_ignore_upper_and_lower_case(client, seeded):
    assert codes(client.get("/api/v1/rooms?building=b")) == ["B-204", "B-205"]
    assert codes(client.get("/api/v1/rooms?room_type=LAB")) == ["B-204", "B-205"]
    assert codes(client.get("/api/v1/rooms?equipment=Projector,COMPUTERS")) == ["B-204"]


def ids_by_name(client, url):
    return {item["name"]: item["id"] for item in client.get(url).get_json()}


def test_rename_room_type_shows_on_its_rooms(client, admin_headers, seeded):
    lab_id = ids_by_name(client, "/api/v1/room-types")["lab"]
    response = client.patch(
        f"/api/v1/room-types/{lab_id}",
        json={"name": "computer_lab", "description": "Room with computers"},
        headers=admin_headers,
    )
    assert response.status_code == 200
    assert response.get_json()["description"] == "Room with computers"
    assert client.get(f"/api/v1/rooms/{seeded['B-204']}").get_json()["room_type"] == "computer_lab"


def test_room_type_update_errors(client, admin_headers, seeded):
    lab_id = ids_by_name(client, "/api/v1/room-types")["lab"]
    url = f"/api/v1/room-types/{lab_id}"
    assert client.patch(url, json={"name": "x"}).status_code == 401
    assert client.patch(url, json={}, headers=admin_headers).status_code == 400
    assert client.patch(url, json={"name": "lecture_hall"}, headers=admin_headers).status_code == 409
    assert client.patch("/api/v1/room-types/9999", json={"name": "x"}, headers=admin_headers).status_code == 404


def test_delete_room_type_only_when_unused(client, admin_headers, seeded):
    lab_id = ids_by_name(client, "/api/v1/room-types")["lab"]
    assert client.delete(f"/api/v1/room-types/{lab_id}", headers=admin_headers).status_code == 409

    created = client.post("/api/v1/room-types", json={"name": "studio"}, headers=admin_headers).get_json()
    assert client.delete(f"/api/v1/room-types/{created['id']}", headers=admin_headers).status_code == 204
    assert "studio" not in ids_by_name(client, "/api/v1/room-types")


def test_rename_equipment_shows_on_its_rooms(client, admin_headers, seeded):
    projector_id = ids_by_name(client, "/api/v1/equipment")["projector"]
    response = client.patch(f"/api/v1/equipment/{projector_id}", json={"name": "beamer"}, headers=admin_headers)
    assert response.status_code == 200
    assert client.get(f"/api/v1/rooms/{seeded['A-101']}").get_json()["equipment"] == ["beamer"]


def test_equipment_update_errors(client, admin_headers, seeded):
    projector_id = ids_by_name(client, "/api/v1/equipment")["projector"]
    url = f"/api/v1/equipment/{projector_id}"
    assert client.patch(url, json={"description": "x"}, headers=admin_headers).status_code == 400
    assert client.patch(url, json={"name": "computers"}, headers=admin_headers).status_code == 409


def test_delete_equipment_only_when_unused(client, admin_headers, seeded):
    equipment = ids_by_name(client, "/api/v1/equipment")
    assert client.delete(f"/api/v1/equipment/{equipment['whiteboard']}", headers=admin_headers).status_code == 409

    # Take the whiteboard out of the only room that has it, then deleting works.
    client.patch(f"/api/v1/rooms/{seeded['B-205']}", json={"equipment": []}, headers=admin_headers)
    assert client.delete(f"/api/v1/equipment/{equipment['whiteboard']}", headers=admin_headers).status_code == 204
    assert "whiteboard" not in ids_by_name(client, "/api/v1/equipment")
