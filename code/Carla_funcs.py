import glob
import os
import sys



try:
    sys.path.append(glob.glob('../PythonAPI/carla/dist/carla-*%d.%d-%s.egg' % (
        sys.version_info.major,
        sys.version_info.minor,
        'win-amd64' if os.name == 'nt' else 'linux-x86_64'))[0])
except IndexError:
    pass


import carla
from queue import Empty

def sensor_callback(data, queue):
    """
    This simple callback just stores the data on a thread safe Python Queue
    to be retrieved from the "main thread".
    """
    queue.put(data)

def setup(collision_queue, image_queue, time_step, img_x, img_y):
    client = carla.Client('localhost', 2000)
    client.set_timeout(10.0)

    # Get the world and its information
    world = client.get_world()
    bp_lib = world.get_blueprint_library()
    original_settings = world.get_settings()

    # Configure the world
    settings = world.get_settings()
    settings.synchronous_mode = True  # make the server wait for the client
    settings.fixed_delta_seconds = time_step
    world.apply_settings(settings)

    # Get the required blueprints
    vehicle_bp = bp_lib.filter('cybertruck')[0]
    camera_bp = bp_lib.filter('sensor.camera.rgb')[0]
    collision_bp = world.get_blueprint_library().find('sensor.other.collision')

    # # Configure the blueprints
    camera_bp.set_attribute("image_size_x", str(img_x))
    camera_bp.set_attribute("image_size_y", str(img_y))
    # Consider adding noise and and blurring with enable_postprocess_effects

    # Spawn our actors
    vehicle = world.spawn_actor(blueprint=vehicle_bp, transform=world.get_map().get_spawn_points()[0])
    camera = world.spawn_actor(blueprint=camera_bp, transform=carla.Transform(carla.Location(x=3.0, z=1.2)),
                               attach_to=vehicle)
    collision = world.spawn_actor(blueprint=collision_bp, transform=carla.Transform(), attach_to=vehicle)

    img_stack = []
    camera.listen(lambda data: sensor_callback(data, image_queue))
    collision.listen(lambda data: sensor_callback(data, collision_queue))

    orig_settings = world.get_settings()

    return client, world, vehicle, camera, collision, orig_settings

def take_action(world, vehicle, image_queue, collision_queue, action, speed = 0.2):
    vehicle.apply_control(carla.VehicleControl(throttle=speed, steer=action))
    world.tick()
    world.get_snapshot().frame

    image_data = image_queue.get(True, 1.0)
    try:
        collision_queue.get_nowait()
        collided = 1
    except Empty:
        collided = 0

    return image_data, collided

def close(world, camera, collision, vehicle, orig_settings):
    # Apply the original settings when exiting.
    world.apply_settings(orig_settings)

    # Destroy the actors in the scene.
    if camera:
        camera.destroy()
    if vehicle:
        vehicle.destroy()
    if collision:
        collision.destroy()