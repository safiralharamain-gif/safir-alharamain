extends Node3D

# SAFIR Hajj & Umrah Training — high-fidelity character prototype v6.
# The male character GLBs are generated in CI from MakeHuman/MPFB CC0 assets.

const NORMAL_GLB := "res://pilgrim_normal.glb"
const IHRAM_GLB := "res://pilgrim_ihram.glb"

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

var wardrobe_pos := Vector3(5.0, 0.0, -3.8)
var miqat_pos := Vector3(0.0, 0.0, -24.0)
var bus_pos := Vector3(5.2, 0.0, -34.0)

var current_clip := ""
var pulse_t := 0.0


func _ready() -> void:
	get_viewport().msaa_3d = Viewport.MSAA_4X
	get_viewport().screen_space_aa = Viewport.SCREEN_SPACE_AA_FXAA
	_build_environment()
	_build_world()
	_build_player()
	_build_hud()
	_build_menu()
	_set_objective(wardrobe_pos + Vector3(0, 2.5, 0))
	_update_hud()
	set_process(true)
	set_physics_process(true)


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

	# Outdoor courtyard / road to miqat
	_box(Vector3(0, -0.16, -30), Vector3(34, 0.30, 42), _mat(Color("#bba98d"),0.90), true)
	for z in range(-13, -49, -5):
		_box(Vector3(-9.0,0.18,float(z)),Vector3(0.65,0.35,3.3),stone,false)
		_box(Vector3(9.0,0.18,float(z)),Vector3(0.65,0.35,3.3),stone,false)

	# Miqat arch
	_box(miqat_pos + Vector3(-2.4,2.1,0), Vector3(0.75,4.2,0.85), stone, false)
	_box(miqat_pos + Vector3(2.4,2.1,0), Vector3(0.75,4.2,0.85), stone, false)
	_box(miqat_pos + Vector3(0,4.05,0), Vector3(5.55,0.55,0.85), stone, false)
	_box(miqat_pos + Vector3(0,4.38,0), Vector3(5.1,0.18,0.90), trim, false)

	# Bus
	var bus := Node3D.new()
	bus.position = bus_pos
	add_child(bus)
	_box(Vector3(0,1.35,0), Vector3(2.9,2.5,7.2), _mat(Color("#f5f0df"),0.35), false, bus)
	_box(Vector3(0,2.05,-0.2), Vector3(2.95,0.75,5.5), glass, false, bus)
	_box(Vector3(0,0.55,0), Vector3(3.02,0.25,7.0), trim, false, bus)
	for wz in [-2.3, 2.3]:
		for wx in [-1.25, 1.25]:
			var wheel := _cylinder(Vector3(wx,0.35,wz),0.43,0.30,black,bus)
			wheel.rotation_degrees.z = 90

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

	var collider := CollisionShape3D.new()
	var capsule := CapsuleShape3D.new()
	capsule.radius = 0.33
	capsule.height = 1.78
	collider.shape = capsule
	collider.position.y = 0.89
	player.add_child(collider)

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
	_add_ihram_wraps(ihram_model)

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


func _add_ihram_wraps(parent: Node3D) -> void:
	var cloth := _mat(Color("#fffdf7"), 0.94)
	# Lower izar wrap: long, slightly flared cloth from waist to ankles.
	var lower := _cylinder(Vector3(0,0.58,0),0.43,1.06,cloth,parent,0.36)
	lower.name = "IhramLower"
	# Upper rida wrap: chest drape. Kept slightly loose so it reads as fabric in third-person.
	var upper := _cylinder(Vector3(0,1.28,0),0.40,0.72,cloth,parent,0.36)
	upper.name = "IhramUpper"
	# Layered hems add visible cloth thickness/folds under lighting.
	for y in [0.08, 1.08, 0.94, 1.63]:
		var hem := _cylinder(Vector3(0,y,0),0.435 if y < 0.7 else 0.405,0.035,_mat(Color("#f1eee6"),0.88),parent)
		hem.name = "IhramHem"


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
	title.text = "شخصيه الحج والعمره 6"
	title.horizontal_alignment = HORIZONTAL_ALIGNMENT_CENTER
	title.add_theme_font_size_override("font_size",42)
	vb.add_child(title)
	var sub := Label.new()
	sub.text = "تدريب ثلاثي الأبعاد — شخصية بشرية Rigged وخامات واقعية"
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
			mission_label.text = "المهمة 2: بعد ارتداء الإحرام، اخرج من الفندق واتجه إلى الميقات."
			progress_label.text = "2 / 3"
		2:
			mission_label.text = "المهمة 3: اتجه إلى الحافلة لبدء الرحلة التالية."
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
	var speed := 5.4 if running else 3.1
	player.velocity.x = wish.x * speed
	player.velocity.z = wish.z * speed
	if not player.is_on_floor():
		player.velocity.y -= 18.0 * delta
	elif Input.is_key_pressed(KEY_SPACE):
		player.velocity.y = 6.0

	if wish.length() > 0.01:
		var target_yaw := atan2(-wish.x, -wish.z)
		visual.rotation.y = lerp_angle(visual.rotation.y, target_yaw, minf(1.0, delta * 10.0))
		_play_clip("run" if running else "walk", 1.10 if running else 1.0)
	else:
		_play_clip("idle", 1.0)

	player.move_and_slide()
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
		var d3 := player.global_position.distance_to(bus_pos)
		if d3 < 3.2:
			msg = "اضغط F لركوب الحافلة"
	interaction_label.text = msg


func _interact() -> void:
	if not started:
		return
	if mission == 0 and player.global_position.distance_to(wardrobe_pos) < 2.35:
		wearing_ihram = true
		normal_model.visible = false
		ihram_model.visible = true
		active_anim = ihram_anim
		current_clip = ""
		_play_clip("idle")
		mission = 1
		_set_objective(miqat_pos + Vector3(0,5.0,0))
		_update_hud()
	elif mission == 1 and player.global_position.distance_to(miqat_pos) < 2.8:
		mission = 2
		_set_objective(bus_pos + Vector3(0,3.4,0))
		_update_hud()
	elif mission == 2 and player.global_position.distance_to(bus_pos) < 3.2:
		mission = 3
		objective_marker.visible = false
		_update_hud()
		var done := complete_panel.get_node("VBoxContainer/DoneText") if complete_panel.has_node("VBoxContainer/DoneText") else null
		if done == null:
			done = complete_panel.find_child("DoneText", true, false)
		if done:
			done.text = ("المسار التالي: مكة والطواف والسعي — سيُبنى على نفس المجسم الواقعي." if training_mode == "umrah" else "المسار التالي: منى وعرفات ومزدلفة والجمرات — سيُبنى على نفس المجسم الواقعي.")
		complete_panel.visible = true
		Input.mouse_mode = Input.MOUSE_MODE_VISIBLE


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
	if objective_marker and objective_marker.visible:
		objective_marker.position.y += sin(pulse_t * 3.0) * 0.0015
		objective_marker.rotation.y += delta * 0.8
		objective_light.light_energy = 1.8 + sin(pulse_t * 4.0) * 0.45
