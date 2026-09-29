extends Node3D

# SAFIR Hajj & Umrah Training — V13 real-mocap movement and moving coach.
# The male character GLBs are generated in CI from MakeHuman/MPFB CC0 assets.

const NORMAL_GLB := "res://pilgrim_normal.glb"
const IHRAM_GLB := "res://pilgrim_ihram.glb"
const SAFIR_BUS_GLB := "res://coach_bus_safir.glb"
const STANDARD_BUS_GLB := "res://coach_bus_standard.glb"
const TRAFFIC_CAR_GLB := "res://traffic_car.glb"
const MIQAT_GLB := "res://miqat_abyar_ali.glb"
const MODEL_FORWARD_OFFSET := PI
const WALK_METERS_PER_SEC := 1.38
const NPC_OLDER_IHRAM := "res://npc_older_ihram.glb"
const NPC_DARK_IHRAM := "res://npc_dark_ihram.glb"
const NPC_YOUNG_NORMAL := "res://npc_young_normal.glb"
const NPC_STOCKY_NORMAL := "res://npc_stocky_normal.glb"
const LABBAYK_AUDIO := "res://labbayk_umrah.mp3"

var player: CharacterBody3D
var visual: Node3D
var normal_model: Node3D
var ihram_model: Node3D
var normal_anim: AnimationPlayer
var ihram_anim: AnimationPlayer
var active_anim: AnimationPlayer

var cam_pivot: Node3D
var spring_arm: SpringArm3D
var camera: Camera3D
var cam_yaw := 0.0
var cam_pitch := -0.12

var started := false
var training_mode := ""
var mission := 0
var wearing_ihram := false
var objective_marker: Node3D
var objective_light: OmniLight3D

var hud_layer: CanvasLayer
var mission_label: Label
var mode_label: Label
var interaction_label: Label
var progress_label: Label
var menu_layer: CanvasLayer
var complete_panel: PanelContainer
var wardrobe_ihram: Node3D
var safir_bus_label: Label3D
var safir_bus_beacon: OmniLight3D

var wardrobe_pos := Vector3(5.0, 0.0, -3.8)
var miqat_pos := Vector3(0.0, 0.0, -31.0)
var bus_pos := Vector3(7.0, 0.0, -58.0)
var bus_board_pos := Vector3(8.95, 0.0, -63.05)

var current_clip := ""
var pulse_t := 0.0
var npc_agents: Array = []
var traffic_cars: Array = []
var parked_buses: Array[Node3D] = []
var preview_t := 0.0
var preview_saved := false
var last_safe_position := Vector3(0,0.10,6.0)
var safir_bus: Node3D
var safir_bus_body: StaticBody3D
var player_collision: CollisionShape3D
var bus_audio: AudioStreamPlayer
var boarded_bus := false
var bus_journey_active := false
var bus_journey_finished := false
var bus_speed := 0.0
var bus_target_speed := 7.5
var bus_distance := 0.0


func _ready() -> void:
	get_viewport().msaa_3d = Viewport.MSAA_4X
	get_viewport().screen_space_aa = Viewport.SCREEN_SPACE_AA_FXAA
	_build_environment()
	_build_world()
	_build_player()
	_build_crowd_and_traffic()
	_build_hud()
	_build_bus_audio()
	_build_menu()
	_set_objective(wardrobe_pos + Vector3(0, 2.5, 0))
	_update_hud()
	set_process(true)
	set_physics_process(true)
	if OS.has_environment("SAFIR_PREVIEW"):
		call_deferred("_setup_preview")


func _build_environment() -> void:
	var sky_mat := ProceduralSkyMaterial.new()
	sky_mat.sky_top_color = Color(0.045, 0.09, 0.16)
	sky_mat.sky_horizon_color = Color(0.72, 0.57, 0.40)
	sky_mat.ground_horizon_color = Color(0.28, 0.22, 0.18)
	sky_mat.ground_bottom_color = Color(0.05, 0.04, 0.04)
	sky_mat.sun_angle_max = 18.0
	sky_mat.sun_curve = 0.08
	var sky := Sky.new()
	sky.sky_material = sky_mat

	var env := Environment.new()
	env.background_mode = Environment.BG_SKY
	env.sky = sky
	env.ambient_light_source = Environment.AMBIENT_SOURCE_SKY
	env.ambient_light_energy = 0.38
	env.reflected_light_source = Environment.REFLECTION_SOURCE_SKY
	env.tonemap_mode = Environment.TONE_MAPPER_AGX
	env.tonemap_exposure = 1.05
	env.ssao_enabled = true
	env.ssao_radius = 1.6
	env.ssao_intensity = 2.0
	env.ssao_power = 1.35
	env.ssil_enabled = true
	env.ssil_radius = 4.0
	env.ssil_intensity = 0.9
	env.glow_enabled = true
	env.glow_intensity = 0.20
	env.glow_bloom = 0.08
	env.fog_enabled = true
	env.fog_light_color = Color(0.72, 0.64, 0.54)
	env.fog_density = 0.0025
	var we := WorldEnvironment.new()
	we.environment = env
	add_child(we)

	var sun := DirectionalLight3D.new()
	sun.light_color = Color(1.0, 0.83, 0.65)
	sun.light_energy = 1.55
	sun.rotation_degrees = Vector3(-46, -35, 0)
	sun.shadow_enabled = true
	sun.shadow_blur = 2.2
	sun.directional_shadow_max_distance = 80.0
	add_child(sun)

	var fill := DirectionalLight3D.new()
	fill.light_color = Color(0.48, 0.62, 0.92)
	fill.light_energy = 0.42
	fill.rotation_degrees = Vector3(-20, 145, 0)
	add_child(fill)


func _mat(color: Color, roughness := 0.55, metallic := 0.0, emission := Color(0,0,0,1)) -> StandardMaterial3D:
	var m := StandardMaterial3D.new()
	m.albedo_color = color
	m.roughness = roughness
	m.metallic = metallic
	if emission.r > 0.0 or emission.g > 0.0 or emission.b > 0.0:
		m.emission_enabled = true
		m.emission = emission
		m.emission_energy_multiplier = 2.0
	return m


func _box(pos: Vector3, size: Vector3, material: Material, collide := false, parent: Node = self) -> Node3D:
	var holder := Node3D.new()
	holder.position = pos
	parent.add_child(holder)
	var mi := MeshInstance3D.new()
	var mesh := BoxMesh.new()
	mesh.size = size
	mi.mesh = mesh
	mi.material_override = material
	mi.cast_shadow = GeometryInstance3D.SHADOW_CASTING_SETTING_ON
	holder.add_child(mi)
	if collide:
		var sb := StaticBody3D.new()
		holder.add_child(sb)
		var cs := CollisionShape3D.new()
		var shape := BoxShape3D.new()
		shape.size = size
		cs.shape = shape
		sb.add_child(cs)
	return holder


func _invisible_collider(pos: Vector3, size: Vector3) -> StaticBody3D:
	var sb := StaticBody3D.new()
	sb.position = pos
	add_child(sb)
	var cs := CollisionShape3D.new()
	var sh := BoxShape3D.new()
	sh.size = size
	cs.shape = sh
	sb.add_child(cs)
	return sb


func _cylinder(pos: Vector3, radius: float, height: float, material: Material, parent: Node = self, top_radius := -1.0) -> MeshInstance3D:
	var mi := MeshInstance3D.new()
	var mesh := CylinderMesh.new()
	mesh.radial_segments = 64
	mesh.rings = 8
	mesh.height = height
	mesh.bottom_radius = radius
	mesh.top_radius = radius if top_radius < 0.0 else top_radius
	mi.mesh = mesh
	mi.material_override = material
	mi.position = pos
	mi.cast_shadow = GeometryInstance3D.SHADOW_CASTING_SETTING_ON
	parent.add_child(mi)
	return mi


func _build_world() -> void:
	var stone := _mat(Color("#d7c8ae"), 0.78)
	var wall := _mat(Color("#efe6d6"), 0.92)
	var trim := _mat(Color("#c7a86a"), 0.36, 0.15)
	var wood := _mat(Color("#5b3828"), 0.58)
	var darkwood := _mat(Color("#2f201a"), 0.48)
	var fabric := _mat(Color("#2e3c51"), 0.90)
	var white := _mat(Color("#f3f0e7"), 0.88)
	var glass := _mat(Color(0.07,0.14,0.20,1), 0.12, 0.20)
	var black := _mat(Color("#12151a"), 0.45, 0.15)

	# Hotel room
	_box(Vector3(0, -0.12, 0), Vector3(16, 0.24, 18), stone, true)
	_box(Vector3(-8, 1.8, 0), Vector3(0.30, 3.6, 18), wall, true)
	_box(Vector3(8, 1.8, 0), Vector3(0.30, 3.6, 18), wall, true)
	_box(Vector3(0, 1.8, 9), Vector3(16, 3.6, 0.30), wall, true)
	_box(Vector3(-5.0, 1.8, -9), Vector3(6.0, 3.6, 0.30), wall, true)
	_box(Vector3(5.0, 1.8, -9), Vector3(6.0, 3.6, 0.30), wall, true)
	_box(Vector3(0, 3.55, 0), Vector3(16, 0.20, 18), white, false)

	# Floor tile detail
	for ix in range(-7, 8):
		for iz in range(-8, 9):
			if (ix + iz) % 2 == 0:
				_box(Vector3(float(ix) + 0.5, 0.015, float(iz) + 0.5), Vector3(0.94, 0.025, 0.94), _mat(Color("#cdbda5"), 0.66), false)

	# Bed + bench + desk
	_box(Vector3(-4.4, 0.35, 3.2), Vector3(3.4, 0.65, 2.2), darkwood, false)
	_box(Vector3(-4.4, 0.82, 3.2), Vector3(3.15, 0.30, 2.0), white, false)
	_box(Vector3(-5.25, 1.05, 3.2), Vector3(1.15, 0.22, 1.65), _mat(Color("#f8f6f0"),0.96), false)
	_box(Vector3(-1.8, 0.45, 5.2), Vector3(2.0, 0.85, 0.75), wood, false)
	_box(Vector3(-1.8, 0.92, 5.2), Vector3(2.1, 0.10, 0.85), trim, false)

	# Wardrobe target
	_box(wardrobe_pos + Vector3(0, 1.35, 0), Vector3(2.5, 2.7, 0.85), wood, true)
	_box(wardrobe_pos + Vector3(-0.63, 1.38, -0.44), Vector3(0.04, 2.45, 0.035), trim, false)
	_box(wardrobe_pos + Vector3(0.63, 1.38, -0.44), Vector3(0.04, 2.45, 0.035), trim, false)
	_cylinder(wardrobe_pos + Vector3(-0.12,1.35,-0.48),0.025,0.16,trim,self)
	_cylinder(wardrobe_pos + Vector3(0.12,1.35,-0.48),0.025,0.16,trim,self)

	# Two-piece ihram visibly hanging inside the wardrobe before the player wears it.
	wardrobe_ihram = Node3D.new()
	wardrobe_ihram.name = "WardrobeIhram"
	wardrobe_ihram.position = wardrobe_pos
	add_child(wardrobe_ihram)
	var ihram_cloth := _mat(Color("#fffdf8"), 0.96)
	var ihram_fold := _mat(Color("#e9e5dc"), 0.90)
	_box(Vector3(0,2.45,-0.47), Vector3(1.72,0.055,0.055), trim, false, wardrobe_ihram)
	# Upper rida piece on the left hanger.
	var hang_upper := _box(Vector3(-0.53,1.67,-0.50), Vector3(0.82,1.15,0.055), ihram_cloth, false, wardrobe_ihram)
	hang_upper.rotation_degrees.z = -4.0
	for fx in [-0.22,0.0,0.22]:
		_box(Vector3(-0.53+fx,1.67,-0.535), Vector3(0.025,1.05,0.018), ihram_fold, false, wardrobe_ihram)
	# Lower izar piece on the right hanger.
	var hang_lower := _box(Vector3(0.50,1.57,-0.50), Vector3(0.80,1.38,0.055), ihram_cloth, false, wardrobe_ihram)
	hang_lower.rotation_degrees.z = 3.0
	for fx in [-0.22,0.0,0.22]:
		_box(Vector3(0.50+fx,1.57,-0.535), Vector3(0.025,1.28,0.018), ihram_fold, false, wardrobe_ihram)

	# Hotel lighting
	for lp in [Vector3(-4,3.15,2), Vector3(3.5,3.15,2), Vector3(0,3.15,-4.5)]:
		var l := OmniLight3D.new()
		l.position = lp
		l.light_color = Color(1.0, 0.79, 0.58)
		l.light_energy = 1.7
		l.omni_range = 7.5
		l.shadow_enabled = true
		add_child(l)

	# Door frame / corridor
	_box(Vector3(-1.65, 1.65, -8.75), Vector3(0.35, 3.3, 0.55), trim, false)
	_box(Vector3(1.65, 1.65, -8.75), Vector3(0.35, 3.3, 0.55), trim, false)
	_box(Vector3(0, 3.15, -8.75), Vector3(3.6, 0.35, 0.55), trim, false)

	# Path from hotel to the real miqat complex.
	_box(Vector3(0, -0.10, -18), Vector3(10, 0.18, 18), _mat(Color("#c6b69b"),0.88), true)
	# Abyar Ali / Dhul Hulayfah inspired environment generated from the user's photo references.
	if ResourceLoader.exists(MIQAT_GLB):
		var miqat_scene := load(MIQAT_GLB) as PackedScene
		var miqat := miqat_scene.instantiate() as Node3D
		miqat.name = "MiqatAbyarAli"
		miqat.position = Vector3(0,0,-35.0)
		add_child(miqat)

	# Gameplay collision floor under the entire miqat model. The imported visual GLB itself
	# deliberately stays render-only, so the player can never fall through decorative meshes.
	_invisible_collider(Vector3(0,-0.24,-35.0), Vector3(48.0,0.45,48.0))
	# Side/far safety walls keep the player inside the training area without visible barriers.
	_invisible_collider(Vector3(-23.8,1.7,-39.0), Vector3(0.45,3.4,56.0))
	_invisible_collider(Vector3(23.8,1.7,-39.0), Vector3(0.45,3.4,56.0))
	_invisible_collider(Vector3(0,1.7,-66.0), Vector3(48.0,3.4,0.45))

	# Main SAFIR coach — black/gold, parked fully behind the miqat curb with >5m facade clearance.
	if ResourceLoader.exists(SAFIR_BUS_GLB):
		var bus_scene := load(SAFIR_BUS_GLB) as PackedScene
		safir_bus = bus_scene.instantiate() as Node3D
		safir_bus.name = "SafirCoach"
		safir_bus.position = bus_pos
		add_child(safir_bus)
	else:
		safir_bus = Node3D.new()
		safir_bus.name = "SafirCoachFallback"
		safir_bus.position = bus_pos
		add_child(safir_bus)
		_box(Vector3(0,1.65,0), Vector3(2.7,3.20,10.6), _mat(Color("#191a1d"),0.24,0.32), false, safir_bus)
		_box(Vector3(0,1.00,0), Vector3(2.75,0.14,10.7), trim, false, safir_bus)

	# Collision around the parked coach. It is disabled when the bus departs.
	safir_bus_body = StaticBody3D.new()
	safir_bus_body.position = bus_pos + Vector3(0,1.65,0)
	add_child(safir_bus_body)
	var bus_col := CollisionShape3D.new()
	var bus_shape := BoxShape3D.new()
	bus_shape.size = Vector3(2.75,3.30,10.8)
	bus_col.shape = bus_shape
	safir_bus_body.add_child(bus_col)

	# Unmistakable marker above the user's SAFIR coach.
	safir_bus_label = Label3D.new()
	safir_bus_label.text = "باص سفير"
	safir_bus_label.font_size = 58
	safir_bus_label.outline_size = 12
	safir_bus_label.modulate = Color("#ffd46b")
	safir_bus_label.outline_modulate = Color(0.06,0.05,0.03,0.95)
	safir_bus_label.billboard = BaseMaterial3D.BILLBOARD_ENABLED
	safir_bus_label.position = bus_pos + Vector3(0,5.2,0)
	add_child(safir_bus_label)
	var beacon_mesh := MeshInstance3D.new()
	var beacon_shape := CylinderMesh.new()
	beacon_shape.top_radius = 0.07
	beacon_shape.bottom_radius = 0.22
	beacon_shape.height = 1.25
	beacon_shape.radial_segments = 32
	beacon_mesh.mesh = beacon_shape
	beacon_mesh.material_override = _mat(Color("#e7b444"),0.22,0.15,Color("#ffbd38"))
	beacon_mesh.position = bus_pos + Vector3(0,4.25,0)
	add_child(beacon_mesh)
	safir_bus_beacon = OmniLight3D.new()
	safir_bus_beacon.position = bus_pos + Vector3(0,4.55,0)
	safir_bus_beacon.light_color = Color("#ffbf45")
	safir_bus_beacon.light_energy = 2.8
	safir_bus_beacon.omni_range = 5.0
	add_child(safir_bus_beacon)

	# Distant structures for depth
	for i in range(9):
		var bx := -15.0 + float(i % 5) * 7.2
		var bz := -46.0 - float(i / 5) * 8.0
		var h := 5.0 + float((i * 7) % 5)
		_box(Vector3(bx,h/2.0,bz),Vector3(5.6,h,5.0),_mat(Color(0.40+0.03*i,0.36,0.31,1),0.85),false)

	# Objective marker
	objective_marker = Node3D.new()
	add_child(objective_marker)
	var ring := MeshInstance3D.new()
	var rm := CylinderMesh.new()
	rm.top_radius = 0.52
	rm.bottom_radius = 0.52
	rm.height = 0.08
	rm.radial_segments = 64
	ring.mesh = rm
	ring.material_override = _mat(Color("#f6c85f"),0.25,0.05,Color("#f6c85f"))
	objective_marker.add_child(ring)
	objective_light = OmniLight3D.new()
	objective_light.light_color = Color("#f6c85f")
	objective_light.light_energy = 2.2
	objective_light.omni_range = 3.0
	objective_marker.add_child(objective_light)


func _build_player() -> void:
	player = CharacterBody3D.new()
	player.name = "Player"
	add_child(player)

	player_collision = CollisionShape3D.new()
	var capsule := CapsuleShape3D.new()
	capsule.radius = 0.33
	capsule.height = 1.78
	player_collision.shape = capsule
	player_collision.position.y = 0.89
	player.add_child(player_collision)

	visual = Node3D.new()
	visual.name = "Visual"
	player.add_child(visual)

	normal_model = _instantiate_character(NORMAL_GLB)
	ihram_model = _instantiate_character(IHRAM_GLB)
	visual.add_child(normal_model)
	visual.add_child(ihram_model)
	ihram_model.visible = false

	normal_anim = _find_class(normal_model, "AnimationPlayer") as AnimationPlayer
	ihram_anim = _find_class(ihram_model, "AnimationPlayer") as AnimationPlayer
	_prepare_anims(normal_anim)
	_prepare_anims(ihram_anim)
	active_anim = normal_anim

	cam_pivot = Node3D.new()
	cam_pivot.position = Vector3(0, 1.45, 0)
	player.add_child(cam_pivot)
	spring_arm = SpringArm3D.new()
	spring_arm.spring_length = 4.7
	spring_arm.margin = 0.18
	spring_arm.collision_mask = 1
	cam_pivot.add_child(spring_arm)
	camera = Camera3D.new()
	camera.current = true
	camera.fov = 58.0
	camera.near = 0.05
	spring_arm.add_child(camera)

	player.position = Vector3(0, 0.10, 6.0)
	_play_clip("idle")


func _instantiate_character(path: String) -> Node3D:
	var ps := load(path) as PackedScene
	if ps == null:
		push_error("Character asset missing: " + path)
		var fallback := Node3D.new()
		_cylinder(Vector3(0,0.9,0),0.30,1.7,_mat(Color("#d1a177"),0.72),fallback)
		return fallback
	var n := ps.instantiate() as Node3D
	n.name = path.get_file().get_basename()
	return n


func _prepare_anims(ap: AnimationPlayer) -> void:
	if ap == null:
		return
	for an in ap.get_animation_list():
		var a := ap.get_animation(an)
		if a:
			a.loop_mode = Animation.LOOP_LINEAR


func _find_class(n: Node, cls: String) -> Node:
	if n.get_class() == cls:
		return n
	for c in n.get_children():
		var r := _find_class(c, cls)
		if r:
			return r
	return null



func _switch_to_ihram() -> void:
	wearing_ihram = true
	if wardrobe_ihram:
		wardrobe_ihram.visible = false
	normal_model.visible = false
	ihram_model.visible = true
	active_anim = ihram_anim
	current_clip = ""
	_play_clip("idle")


func _load_scene(path: String) -> PackedScene:
	if ResourceLoader.exists(path):
		return load(path) as PackedScene
	return null


func _spawn_bus(pos: Vector3, yaw: float = 0.0) -> void:
	var ps := _load_scene(STANDARD_BUS_GLB)
	if ps == null:
		return
	var b := ps.instantiate() as Node3D
	b.position = pos
	b.rotation.y = yaw
	b.scale = Vector3.ONE * 0.96
	add_child(b)
	parked_buses.append(b)
	var sb := StaticBody3D.new()
	sb.position = pos + Vector3(0,1.58,0)
	sb.rotation.y = yaw
	add_child(sb)
	var cs := CollisionShape3D.new()
	var shape := BoxShape3D.new()
	shape.size = Vector3(2.68,3.18,10.3)
	cs.shape = shape
	sb.add_child(cs)


func _spawn_car(pos: Vector3, lane_dir: float, speed: float, tint: Color) -> void:
	var ps := _load_scene(TRAFFIC_CAR_GLB)
	if ps == null:
		return
	var car := ps.instantiate() as Node3D
	car.position = pos
	car.rotation.y = 0.0 if lane_dir < 0.0 else PI
	add_child(car)
	# Slight material tint variation on the body only.
	_tint_named_meshes(car, "Body", tint)
	traffic_cars.append({"node":car, "dir":lane_dir, "speed":speed, "start_z":pos.z})


func _tint_named_meshes(n: Node, pattern: String, color: Color) -> void:
	if n is MeshInstance3D and n.name.to_lower().contains(pattern.to_lower()):
		var mi := n as MeshInstance3D
		var m := StandardMaterial3D.new()
		m.albedo_color = color
		m.metallic = 0.66
		m.roughness = 0.20
		mi.material_override = m
	for ch in n.get_children():
		_tint_named_meshes(ch, pattern, color)


func _spawn_npc(path: String, start: Vector3, points: Array[Vector3], speed: float, scale_v: float = 1.0, delay: float = 0.0, board := false) -> void:
	var ps := _load_scene(path)
	if ps == null:
		return
	var n := ps.instantiate() as Node3D
	n.position = start
	n.scale = Vector3.ONE * scale_v
	add_child(n)
	var ap := _find_class(n, "AnimationPlayer") as AnimationPlayer
	_prepare_anims(ap)
	if ap and ap.has_animation("walk"):
		# Match animation cadence to actual world speed so feet plant instead of sliding.
		var anim_speed := clampf(speed / WALK_METERS_PER_SEC, 0.55, 1.05)
		ap.play("walk", 0.25, anim_speed)
	npc_agents.append({
		"node": n,
		"anim": ap,
		"start": start,
		"points": points,
		"idx": 0,
		"speed": speed,
		"delay": delay,
		"board": board,
		"hidden_time": 0.0
	})


func _build_crowd_and_traffic() -> void:
	# Bus parking apron beyond the miqat complex.
	var asphalt := _mat(Color("#34373b"),0.94)
	var line_mat := _mat(Color("#eee3b6"),0.72)
	_box(Vector3(0,-0.06,-62.0),Vector3(46,0.12,34.0),asphalt,true)
	for x in [-12.0,-6.0,0.0,6.0,12.0]:
		_box(Vector3(x,0.02,-61.0),Vector3(0.10,0.012,27.0),line_mat,false)

	# Modern coach fleet around the miqat parking area.
	_spawn_bus(Vector3(-11.0,0,-58.0),0.02)
	_spawn_bus(Vector3(-5.0,0,-58.0),0.01)
	_spawn_bus(Vector3(1.0,0,-58.0),-0.01)
	_spawn_bus(Vector3(13.0,0,-58.0),0.02)
	_spawn_bus(Vector3(-11.0,0,-70.0),PI)
	_spawn_bus(Vector3(-3.0,0,-70.0),PI)
	_spawn_bus(Vector3(5.0,0,-70.0),PI)
	_spawn_bus(Vector3(13.0,0,-70.0),PI)

	# Moving cars at the edge of the bus lot.
	# Cars stay on two dedicated edge lanes in the parking apron; they no longer cross the mosque walls.
	_spawn_car(Vector3(-20.4,0,-54.0),-1.0,4.4,Color("#233d68"))
	_spawn_car(Vector3(-18.6,0,-76.0),1.0,4.0,Color("#777b80"))
	_spawn_car(Vector3(20.4,0,-58.0),-1.0,4.7,Color("#7b2525"))
	_spawn_car(Vector3(18.6,0,-72.0),1.0,3.9,Color("#d2ccc0"))

	var board_pt := bus_board_pos

	# Boarding queue at the user's black/gold SAFIR coach.
	_spawn_npc(NPC_OLDER_IHRAM,Vector3(2.0,0,-39.0),
		[Vector3(1.0,0,-44.0),Vector3(0.0,0,-48.5),Vector3(4.5,0,-54.0),board_pt],0.95,1.00,0.0,true)
	_spawn_npc(NPC_DARK_IHRAM,Vector3(-1.0,0,-38.0),
		[Vector3(0.0,0,-44.0),Vector3(0.0,0,-48.5),Vector3(4.0,0,-54.5),board_pt+Vector3(0,0,0.8)],1.02,1.03,1.8,true)
	_spawn_npc(NPC_YOUNG_NORMAL,Vector3(4.0,0,-37.0),
		[Vector3(1.0,0,-44.0),Vector3(0.0,0,-48.5),Vector3(5.0,0,-55.0),board_pt+Vector3(0,0,1.45)],1.05,0.96,3.3,true)

	# People moving through the palm-lined courtyard and arcades.
	_spawn_npc(NPC_STOCKY_NORMAL,Vector3(-7.5,0,-25.0),
		[Vector3(-6.0,0,-30.0),Vector3(-4.0,0,-35.0),Vector3(-2.0,0,-40.0)],0.86,1.02,0.5,false)
	_spawn_npc(NPC_DARK_IHRAM,Vector3(7.5,0,-26.0),
		[Vector3(6.0,0,-31.0),Vector3(4.0,0,-36.0),Vector3(2.0,0,-40.0)],0.92,0.98,1.0,false)
	_spawn_npc(NPC_OLDER_IHRAM,Vector3(-3.5,0,-29.0),
		[Vector3(-2.0,0,-33.0),Vector3(0.0,0,-36.5),Vector3(2.5,0,-39.0)],0.82,0.97,2.2,false)
	_spawn_npc(NPC_YOUNG_NORMAL,Vector3(3.0,0,-28.0),
		[Vector3(1.5,0,-32.0),Vector3(-0.5,0,-35.5),Vector3(-3.0,0,-39.0)],0.90,1.00,0.0,false)

	# Extra groups around other coaches.
	_spawn_npc(NPC_OLDER_IHRAM,Vector3(-12.0,0,-46.0),
		[Vector3(-11.0,0,-49.5),Vector3(-10.8,0,-52.0)],0.76,1.03,0.0,false)
	_spawn_npc(NPC_STOCKY_NORMAL,Vector3(11.5,0,-45.0),
		[Vector3(12.0,0,-49.0),Vector3(13.0,0,-52.0)],0.80,1.04,0.0,false)

	# Luggage beside the SAFIR coach.
	var bag_a := _mat(Color("#54402f"),0.78)
	var bag_b := _mat(Color("#243041"),0.74)
	for item in [
		[bus_pos+Vector3(-2.05,0.28,-2.6),Vector3(0.52,0.56,0.34),bag_a],
		[bus_pos+Vector3(-1.95,0.35,-1.95),Vector3(0.44,0.70,0.30),bag_b],
		[bus_pos+Vector3(-1.45,0.24,-2.25),Vector3(0.58,0.48,0.38),bag_a]
	]:
		_box(item[0],item[1],item[2],false)


func _update_lively_world(delta: float) -> void:
	# NPC walking / boarding loops.
	for a in npc_agents:
		var n: Node3D = a["node"]
		if a["hidden_time"] > 0.0:
			a["hidden_time"] -= delta
			if a["hidden_time"] <= 0.0:
				n.visible = true
				n.position = a["start"]
				a["idx"] = 0
				a["delay"] = 0.8
			continue
		if a["delay"] > 0.0:
			a["delay"] -= delta
			continue
		var pts: Array = a["points"]
		if pts.is_empty():
			continue
		var idx: int = a["idx"]
		var target: Vector3 = pts[idx]
		var v := target - n.position
		v.y = 0
		if v.length() < 0.32:
			idx += 1
			if idx >= pts.size():
				if a["board"]:
					n.visible = false
					a["hidden_time"] = 3.2
					continue
				idx = 0
				n.position = a["start"]
				a["delay"] = 1.0
			a["idx"] = idx
			continue
		var dir := v.normalized()
		n.position += dir * float(a["speed"]) * delta
		n.rotation.y = lerp_angle(n.rotation.y,atan2(-dir.x,-dir.z) + MODEL_FORWARD_OFFSET,minf(1.0,delta*5.0))

	# Cars move continuously along the road and wrap around.
	for info in traffic_cars:
		var car: Node3D = info["node"]
		var d: float = info["dir"]
		car.position.z += d * float(info["speed"]) * delta
		if d < 0.0 and car.position.z < -79.0:
			car.position.z = -52.0
		elif d > 0.0 and car.position.z > -52.0:
			car.position.z = -79.0


func _setup_preview() -> void:
	_start_mode("umrah")
	_switch_to_ihram()
	mission = 2
	player.position = Vector3(2.0,0.08,-28.3)
	visual.rotation.y = -0.35
	cam_yaw = -0.75
	cam_pitch = -0.13
	_update_hud()


func _save_preview_if_needed(delta: float) -> void:
	if not OS.has_environment("SAFIR_PREVIEW") or preview_saved:
		return
	preview_t += delta
	if preview_t < 3.0:
		return
	preview_saved = true
	var img := get_viewport().get_texture().get_image()
	var out_path := OS.get_environment("SAFIR_PREVIEW_PATH")
	if out_path.is_empty():
		out_path = ProjectSettings.globalize_path("user://preview.png")
	print("[preview] saving to ", out_path)
	var err := img.save_png(out_path)
	print("[preview] save result=", err)
	get_tree().quit()

func _build_bus_audio() -> void:
	bus_audio = AudioStreamPlayer.new()
	bus_audio.name = "LabbaykUmrahAudio"
	if ResourceLoader.exists(LABBAYK_AUDIO):
		bus_audio.stream = load(LABBAYK_AUDIO)
		bus_audio.volume_db = -1.5
	add_child(bus_audio)


func _start_bus_journey() -> void:
	if boarded_bus or safir_bus == null:
		return
	boarded_bus = true
	bus_journey_active = true
	bus_journey_finished = false
	bus_speed = 0.0
	bus_distance = 0.0

	# The pilgrim is now inside the coach, so hide the exterior character and disable its collision.
	visual.visible = false
	if player_collision:
		player_collision.set_deferred("disabled", true)
	player.velocity = Vector3.ZERO

	# Remove parking-only markers and collision before the coach moves.
	if objective_marker:
		objective_marker.visible = false
	if safir_bus_body:
		safir_bus_body.queue_free()
		safir_bus_body = null

	# Follow the moving coach from a comfortable third-person/cinematic angle.
	player.global_position = safir_bus.global_position + Vector3(0.0, 1.4, 1.7)
	cam_yaw = 0.0
	cam_pitch = -0.10
	spring_arm.spring_length = 6.8
	camera.fov = 62.0

	# Play the user's uploaded talbiyah/niyyah recording once at departure.
	if training_mode == "umrah" and bus_audio and bus_audio.stream:
		bus_audio.play()

	interaction_label.text = ""
	mission_label.text = "انطلق باص سفير من ميقات أبيار علي إلى مكة"
	progress_label.text = "🚌 الرحلة بدأت"


func _update_bus_journey(delta: float) -> void:
	if not bus_journey_active or safir_bus == null:
		return

	# Smooth acceleration from the parking bay.
	bus_speed = move_toward(bus_speed, bus_target_speed, 2.2 * delta)
	var dz := bus_speed * delta
	bus_distance += dz
	safir_bus.position.z -= dz

	# Keep the floating SAFIR marker travelling with the coach.
	if safir_bus_label:
		safir_bus_label.position = safir_bus.global_position + Vector3(0,5.2,0)
	if safir_bus_beacon:
		safir_bus_beacon.position = safir_bus.global_position + Vector3(0,4.55,0)

	# Camera/player proxy rides inside the coach.
	player.global_position = safir_bus.global_position + Vector3(0.0,1.45,1.7)
	player.velocity = Vector3.ZERO

	# After leaving the miqat compound, complete this leg and hold the moving-road view.
	if bus_distance >= 34.0 and not bus_journey_finished:
		bus_journey_finished = true
		bus_journey_active = false
		bus_speed = 0.0
		mission = 4
		_update_hud()
		mission_label.text = "تم مغادرة ميقات أبيار علي — الطريق إلى مكة"
		progress_label.text = "✓ انطلقت الرحلة"
		complete_panel.visible = true
		var done := complete_panel.find_child("DoneText", true, false)
		if done:
			done.text = "تم ركوب باص سفير والانطلاق من الميقات. المرحلة التالية: الوصول إلى مكة."
		Input.mouse_mode = Input.MOUSE_MODE_VISIBLE


func _build_hud() -> void:
	hud_layer = CanvasLayer.new()
	hud_layer.layer = 10
	add_child(hud_layer)

	var panel := PanelContainer.new()
	panel.set_anchors_preset(Control.PRESET_TOP_RIGHT)
	panel.position = Vector2(-510, 24)
	panel.size = Vector2(480, 150)
	hud_layer.add_child(panel)
	var vb := VBoxContainer.new()
	vb.add_theme_constant_override("separation", 6)
	panel.add_child(vb)

	mode_label = Label.new()
	mode_label.horizontal_alignment = HORIZONTAL_ALIGNMENT_RIGHT
	mode_label.add_theme_font_size_override("font_size", 21)
	vb.add_child(mode_label)
	mission_label = Label.new()
	mission_label.horizontal_alignment = HORIZONTAL_ALIGNMENT_RIGHT
	mission_label.autowrap_mode = TextServer.AUTOWRAP_WORD_SMART
	mission_label.add_theme_font_size_override("font_size", 24)
	vb.add_child(mission_label)
	progress_label = Label.new()
	progress_label.horizontal_alignment = HORIZONTAL_ALIGNMENT_RIGHT
	progress_label.add_theme_font_size_override("font_size", 18)
	vb.add_child(progress_label)

	interaction_label = Label.new()
	interaction_label.set_anchors_preset(Control.PRESET_CENTER_BOTTOM)
	interaction_label.position = Vector2(-320,-105)
	interaction_label.size = Vector2(640,60)
	interaction_label.horizontal_alignment = HORIZONTAL_ALIGNMENT_CENTER
	interaction_label.vertical_alignment = VERTICAL_ALIGNMENT_CENTER
	interaction_label.add_theme_font_size_override("font_size", 25)
	interaction_label.add_theme_color_override("font_color", Color("#fff2c7"))
	hud_layer.add_child(interaction_label)

	complete_panel = PanelContainer.new()
	complete_panel.set_anchors_preset(Control.PRESET_CENTER)
	complete_panel.position = Vector2(-310,-115)
	complete_panel.size = Vector2(620,230)
	complete_panel.visible = false
	hud_layer.add_child(complete_panel)
	var done := VBoxContainer.new()
	done.alignment = BoxContainer.ALIGNMENT_CENTER
	complete_panel.add_child(done)
	var t := Label.new()
	t.text = "✓ تمت مرحلة الجودة الواقعية"
	t.horizontal_alignment = HORIZONTAL_ALIGNMENT_CENTER
	t.add_theme_font_size_override("font_size", 34)
	done.add_child(t)
	var sub := Label.new()
	sub.name = "DoneText"
	sub.horizontal_alignment = HORIZONTAL_ALIGNMENT_CENTER
	sub.autowrap_mode = TextServer.AUTOWRAP_WORD_SMART
	sub.add_theme_font_size_override("font_size", 21)
	done.add_child(sub)


func _build_menu() -> void:
	menu_layer = CanvasLayer.new()
	menu_layer.layer = 50
	add_child(menu_layer)
	var bg := ColorRect.new()
	bg.color = Color(0.015,0.018,0.026,0.965)
	bg.set_anchors_preset(Control.PRESET_FULL_RECT)
	menu_layer.add_child(bg)

	var panel := PanelContainer.new()
	panel.set_anchors_preset(Control.PRESET_CENTER)
	panel.position = Vector2(-360,-255)
	panel.size = Vector2(720,510)
	menu_layer.add_child(panel)
	var vb := VBoxContainer.new()
	vb.alignment = BoxContainer.ALIGNMENT_CENTER
	vb.add_theme_constant_override("separation",18)
	panel.add_child(vb)
	var title := Label.new()
	title.text = "شخصيه الحج والعمره 13"
	title.horizontal_alignment = HORIZONTAL_ALIGNMENT_CENTER
	title.add_theme_font_size_override("font_size",42)
	vb.add_child(title)
	var sub := Label.new()
	sub.text = "تدريب ثلاثي الأبعاد — ركوب باص متحرك، صوت التلبية عند الانطلاق، ومتابعة سينمائية للرحلة"
	sub.horizontal_alignment = HORIZONTAL_ALIGNMENT_CENTER
	sub.add_theme_font_size_override("font_size",20)
	vb.add_child(sub)

	var umrah := Button.new()
	umrah.text = "🕋  لعبة التدريب على العمرة"
	umrah.custom_minimum_size = Vector2(560,76)
	umrah.add_theme_font_size_override("font_size",26)
	umrah.pressed.connect(func(): _start_mode("umrah"))
	vb.add_child(umrah)

	var hajj := Button.new()
	hajj.text = "⛺  لعبة التدريب على الحج"
	hajj.custom_minimum_size = Vector2(560,76)
	hajj.add_theme_font_size_override("font_size",26)
	hajj.pressed.connect(func(): _start_mode("hajj"))
	vb.add_child(hajj)

	var controls := Label.new()
	controls.text = "WASD / الأسهم: حركة   •   Shift: جري   •   Space: قفز   •   F: تفاعل   •   الماوس: الكاميرا"
	controls.horizontal_alignment = HORIZONTAL_ALIGNMENT_CENTER
	controls.autowrap_mode = TextServer.AUTOWRAP_WORD_SMART
	controls.add_theme_font_size_override("font_size",16)
	vb.add_child(controls)


func _start_mode(which: String) -> void:
	training_mode = which
	started = true
	mission = 0
	last_safe_position = player.global_position
	menu_layer.visible = false
	hud_layer.visible = true
	Input.mouse_mode = Input.MOUSE_MODE_CAPTURED
	_set_objective(wardrobe_pos + Vector3(0,2.5,0))
	_update_hud()


func _update_hud() -> void:
	if mode_label == null:
		return
	mode_label.text = "المسار: " + ("التدريب على العمرة" if training_mode == "umrah" else "التدريب على الحج")
	match mission:
		0:
			mission_label.text = "المهمة 1: توجّه إلى خزانة الملابس وارتدِ الإحرام."
			progress_label.text = "1 / 3"
		1:
			mission_label.text = "المهمة 2: اخرج إلى ميقات أبيار علي وامشِ خلال الساحة حتى نقطة النسك."
			progress_label.text = "2 / 3"
		2:
			mission_label.text = "المهمة 3: اخرج إلى موقف الحافلات واعثر على باص سفير الأسود والذهبي."
			progress_label.text = "3 / 3"
		_:
			mission_label.text = "تمت مرحلة التدريب الحالية."
			progress_label.text = "✓"


func _set_objective(pos: Vector3) -> void:
	if objective_marker:
		objective_marker.global_position = pos
		objective_marker.visible = true


func _physics_process(delta: float) -> void:
	if not started:
		return
	if boarded_bus:
		_update_bus_journey(delta)
		cam_pivot.rotation.y = cam_yaw
		spring_arm.rotation.x = cam_pitch
		return
	var inp := Vector2.ZERO
	if Input.is_key_pressed(KEY_A) or Input.is_key_pressed(KEY_LEFT): inp.x -= 1.0
	if Input.is_key_pressed(KEY_D) or Input.is_key_pressed(KEY_RIGHT): inp.x += 1.0
	if Input.is_key_pressed(KEY_W) or Input.is_key_pressed(KEY_UP): inp.y -= 1.0
	if Input.is_key_pressed(KEY_S) or Input.is_key_pressed(KEY_DOWN): inp.y += 1.0
	inp = inp.normalized()

	var yaw_basis := Basis(Vector3.UP, cam_yaw)
	var wish := yaw_basis * Vector3(inp.x, 0, inp.y)
	wish.y = 0
	if wish.length() > 0.01:
		wish = wish.normalized()

	var running := Input.is_key_pressed(KEY_SHIFT)
	# Tuned to the mocap stride so the feet no longer look like they are skating.
	var speed := 2.42 if running else WALK_METERS_PER_SEC
	var target_x := wish.x * speed
	var target_z := wish.z * speed
	var accel := 12.0 if wish.length() > 0.01 else 16.0
	player.velocity.x = move_toward(player.velocity.x, target_x, accel * delta)
	player.velocity.z = move_toward(player.velocity.z, target_z, accel * delta)
	if not player.is_on_floor():
		player.velocity.y -= 18.0 * delta
	elif Input.is_key_pressed(KEY_SPACE):
		player.velocity.y = 5.4

	if wish.length() > 0.01:
		var target_yaw := atan2(-wish.x, -wish.z)
		visual.rotation.y = lerp_angle(visual.rotation.y, target_yaw + MODEL_FORWARD_OFFSET, minf(1.0, delta * 7.0))
		_play_clip("walk", 1.72 if running else 1.0)
	else:
		_play_clip("idle", 1.0)

	player.move_and_slide()
	# Hard safety net: if physics ever drops the player below the decorative scene or outside
	# the training compound, return to the last valid position instead of falling into space.
	var gp := player.global_position
	var valid: bool = gp.y > -1.5 and abs(gp.x) < 23.2 and gp.z > -65.5 and gp.z < 9.0
	if valid:
		last_safe_position = gp
	else:
		player.global_position = last_safe_position
		player.velocity = Vector3.ZERO
	cam_pivot.rotation.y = cam_yaw
	spring_arm.rotation.x = cam_pitch
	_update_interaction()


func _play_clip(name: String, speed := 1.0) -> void:
	if active_anim == null or not active_anim.has_animation(name):
		return
	if current_clip != name:
		current_clip = name
		active_anim.play(name, 0.20, speed)
	else:
		active_anim.speed_scale = speed


func _update_interaction() -> void:
	var msg := ""
	if mission == 0:
		var d := player.global_position.distance_to(wardrobe_pos)
		if d < 2.35:
			msg = "اضغط F لارتداء الإحرام"
	elif mission == 1:
		var d2 := player.global_position.distance_to(miqat_pos)
		if d2 < 2.8:
			msg = "اضغط F عند الميقات لبدء النسك"
	elif mission == 2:
		var d3 := player.global_position.distance_to(bus_board_pos)
		if d3 < 3.2:
			msg = "اضغط F لركوب الحافلة"
	interaction_label.text = msg


func _interact() -> void:
	if not started:
		return
	if mission == 0 and player.global_position.distance_to(wardrobe_pos) < 2.35:
		_switch_to_ihram()
		mission = 1
		_set_objective(miqat_pos + Vector3(0,5.0,0))
		_update_hud()
	elif mission == 1 and player.global_position.distance_to(miqat_pos) < 2.8:
		mission = 2
		_set_objective(bus_board_pos + Vector3(0,2.8,0))
		_update_hud()
	elif mission == 2 and player.global_position.distance_to(bus_board_pos) < 2.3:
		mission = 3
		_start_bus_journey()


func _unhandled_input(event: InputEvent) -> void:
	if not started:
		return
	if event is InputEventMouseMotion and Input.mouse_mode == Input.MOUSE_MODE_CAPTURED:
		cam_yaw -= event.relative.x * 0.0026
		cam_pitch = clampf(cam_pitch - event.relative.y * 0.0023, -0.55, 0.55)
	elif event is InputEventMouseButton and event.pressed:
		if Input.mouse_mode != Input.MOUSE_MODE_CAPTURED:
			Input.mouse_mode = Input.MOUSE_MODE_CAPTURED
	elif event is InputEventKey and event.pressed and not event.echo:
		if event.keycode == KEY_F or event.keycode == KEY_ENTER:
			_interact()
		elif event.keycode == KEY_ESCAPE:
			Input.mouse_mode = Input.MOUSE_MODE_VISIBLE


func _process(delta: float) -> void:
	pulse_t += delta
	_update_lively_world(delta)
	_save_preview_if_needed(delta)
	if safir_bus_beacon:
		safir_bus_beacon.light_energy = 2.4 + sin(pulse_t * 3.5) * 0.6
	if safir_bus_label and not boarded_bus:
		safir_bus_label.position.y = bus_pos.y + 5.15 + sin(pulse_t * 1.8) * 0.08
	if objective_marker and objective_marker.visible:
		objective_marker.position.y += sin(pulse_t * 3.0) * 0.0015
		objective_marker.rotation.y += delta * 0.8
		objective_light.light_energy = 1.8 + sin(pulse_t * 4.0) * 0.45
