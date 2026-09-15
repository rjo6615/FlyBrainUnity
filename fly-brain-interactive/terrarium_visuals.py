"""Low-cost MJCF presentation helpers for the interactive terrarium.

Natural details are visual-only, while the substrate and glass panels are
physical. Wall contacts are consumed by the mechanosensory pathway; decorative
geoms remain outside every sensory system.
"""

TERRARIUM_HALF_SIZE = 32.0


def add_terrarium_shell(root, half_size=TERRARIUM_HALF_SIZE):
    """Add a shallow glass enclosure, earthy substrate, and sparse scale props."""
    asset, world = root.asset, root.worldbody
    materials = {
        "soil": ((0.20, 0.145, 0.09, 1), 0.0),
        "frame": ((0.18, 0.20, 0.19, 1), 0.18),
        "glass": ((0.72, 0.86, 0.88, 0.16), 0.08),
        "bark": ((0.28, 0.16, 0.075, 1), 0.02),
        "stone": ((0.32, 0.31, 0.28, 1), 0.06),
        "moss": ((0.20, 0.30, 0.12, 1), 0.0),
        "leaf": ((0.30, 0.25, 0.09, 1), 0.0),
        "soil_light": ((0.27, 0.19, 0.105, 1), 0.0),
        "soil_dark": ((0.145, 0.095, 0.055, 1), 0.0),
    }
    mats = {}
    for name, (rgba, reflectance) in materials.items():
        mats[name] = asset.add("material", name=f"terrarium_{name}",
                               rgba=rgba, reflectance=reflectance)

    world.add("geom", name="ground", type="box",
              size=(half_size, half_size, 0.35), pos=(0, 0, -0.35),
              material=mats["soil"], friction=(1, 0.005, 0.0001),
              conaffinity=0)

    # Paper-thin, non-colliding patches enrich the substrate without changing
    # the perfectly stable walking/contact surface beneath them.
    for i, (pos, size, mat, yaw) in enumerate((
            ((-13, 7, .012), (10, 6, .012), "soil_light", .24),
            ((12, -13, .011), (8, 5, .011), "soil_dark", -.37),
            ((18, 13, .010), (6, 8, .010), "soil_light", .52))):
        world.add("geom", name=f"decor_substrate_patch_{i}", type="ellipsoid",
                  pos=pos, size=size, euler=(0, 0, yaw), material=mats[mat],
                  contype=0, conaffinity=0)

    # Thin glass panels and a dark laboratory frame define the finite volume.
    wall_h, glass_t = 10.0, 0.18
    for i, (pos, size) in enumerate((
            ((0, half_size, wall_h / 2), (half_size, glass_t, wall_h / 2)),
            ((0, -half_size, wall_h / 2), (half_size, glass_t, wall_h / 2)),
            ((half_size, 0, wall_h / 2), (glass_t, half_size, wall_h / 2)),
            ((-half_size, 0, wall_h / 2), (glass_t, half_size, wall_h / 2)))):
        world.add("geom", name=f"terrarium_glass_{i}", type="box", pos=pos,
                  size=size, material=mats["glass"], contype=1, conaffinity=1,
                  friction=(0.35, 0.005, 0.0001))
    for z in (0.35, wall_h):
        for i, (pos, size) in enumerate((
                ((0, half_size, z), (half_size + .5, .35, .35)),
                ((0, -half_size, z), (half_size + .5, .35, .35)),
                ((half_size, 0, z), (.35, half_size + .5, .35)),
                ((-half_size, 0, z), (.35, half_size + .5, .35)))):
            world.add("geom", name=f"terrarium_frame_{z}_{i}", type="box",
                      pos=pos, size=size, material=mats["frame"],
                      contype=0, conaffinity=0)

    # A deliberately small set of primitive, non-colliding natural details.
    props = (
        ("bark_a", "box", (-19, 14, .75), (6, 1.1, .7), "bark", (0, 0, .30)),
        ("bark_b", "capsule", (20, 16, .8), (1.0, 5.5), "bark", (0, 1.35, .25)),
        ("pebble_a", "ellipsoid", (-23, -15, .8), (2.5, 1.8, .8), "stone", (0, 0, 0)),
        ("pebble_b", "ellipsoid", (23, -18, .65), (1.8, 1.5, .65), "stone", (0, 0, 0)),
        ("moss_a", "cylinder", (-14, -20, .06), (4.0, .06), "moss", (0, 0, 0)),
        ("moss_b", "cylinder", (14, 22, .05), (3.2, .05), "moss", (0, 0, 0)),
        ("leaf_a", "ellipsoid", (17, -10, .12), (4.0, 1.7, .10), "leaf", (0, 0, -.45)),
        ("leaf_b", "ellipsoid", (-7, 19, .10), (3.2, 1.3, .08), "leaf", (0, 0, .72)),
        ("pebble_c", "ellipsoid", (7, 13, .42), (1.2, .9, .42), "stone", (0, 0, .2)),
        ("pebble_d", "ellipsoid", (-4, -16, .32), (.8, 1.1, .32), "stone", (0, 0, -.4)),
    )
    for name, kind, pos, size, material, euler in props:
        world.add("geom", name=f"decor_{name}", type=kind, pos=pos,
                  size=size, euler=euler, material=mats[material],
                  contype=0, conaffinity=0)
    return mats
