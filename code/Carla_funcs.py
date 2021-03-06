# IMPORT LIBRARIES

import glob
import os
import sys
import numpy as np
import cv2
from queue import Queue
from queue import Empty
import random

try:
    sys.path.append(glob.glob('../PythonAPI/carla/dist/carla-*%d.%d-%s.egg' % (
        sys.version_info.major,
        sys.version_info.minor,
        'win-amd64' if os.name == 'nt' else 'linux-x86_64'))[0])
except IndexError:
    pass


import carla


def sensor_callback(data, queue):
    """
    This simple callback just stores the data on a thread safe Python Queue
    to be retrieved from the "main thread".
    """
    queue.put(data)

def setup(time_step, img_x, img_y, speed = 0.2):
    setup_queues = 0
    setup_client_bp_world = 0
    configure_world = 0
    get_bp = 0
    conf_bp = 0
    spawn_actors = 0
    tick_snapshot = 0
    speed_vec = 0

    
    try:

        try:
            client = carla.Client('localhost', 2000)
            client.set_timeout(10.0)
        except:
            print("Connection to server Failed")

        # A vector of random spwan points within the map
        #spawn = random.choice([0,1,7,9,30,50,80])
        spawn = 0

        #setup Queues
        setup_queues = 1
        image_queue = Queue()
        collision_queue = Queue()

        # Get the world and its information
        setup_client_bp_world = 1
        world = client.get_world()
        bp_lib = world.get_blueprint_library()
        orig_settings = world.get_settings()

        # Configure the world
        configure_world = 1
        settings = world.get_settings()
        settings.synchronous_mode = True  # make the server wait for the client
        settings.fixed_delta_seconds = time_step
        configure_world = 1
        world.apply_settings(settings)

        # Get the required blueprints
        get_bp = 1
        vehicle_bp = bp_lib.filter('cybertruck')[0]
        camera_bp = bp_lib.filter('sensor.camera.rgb')[0]
        collision_bp = world.get_blueprint_library().find('sensor.other.collision')

        # Configure the blueprints
        conf_bp = 1
        camera_bp.set_attribute("image_size_x", str(img_x))
        camera_bp.set_attribute("image_size_y", str(img_y))
        
        # Spawn our actors
        spawn_actors = 1
        vehicle = world.spawn_actor(blueprint=vehicle_bp, transform=world.get_map().get_spawn_points()[spawn])
        
        camera = world.spawn_actor(blueprint=camera_bp, transform=carla.Transform(carla.Location(x=3.0, z=1.2)),
                                    attach_to=vehicle)
        collision = world.spawn_actor(blueprint=collision_bp, transform=carla.Transform(), attach_to=vehicle)

        camera.listen(lambda data: sensor_callback(data, image_queue))
        collision.listen(lambda data: sensor_callback(data, collision_queue))

        tick_snapshot = 1
        world.tick()
        world.get_snapshot().frame

        speed_vec = 1
        speed_vec = carla.Vector3D(x=speed, y=0.0, z=0.0)
        vehicle.enable_constant_velocity(speed_vec)

        return client, world, vehicle, camera, collision, orig_settings, image_queue, collision_queue
    
    except:
        print(f'{str(setup_queues)} = {setup_queues}')
        print(f'{str(setup_client_bp_world)} = {setup_client_bp_world}')
        print(f'{str(configure_world)} = {configure_world}')
        print(f'{str(get_bp)} = {get_bp}')
        print(f'{str(conf_bp)} = {conf_bp}')
        print(f'{str(spawn_actors)} = {spawn_actors}')
        print(f'{str(tick_snapshot)} = {tick_snapshot}')
        print(f'{str(speed_vec)} = {speed_vec}')
        # world.apply_settings(orig_settings)

        # Destroy the actors in the scene.
        if camera:
            camera.destroy()
        if vehicle:
            vehicle.destroy()
        if collision:
            collision.destroy()
    
def spawn_car(world, img_x = 128, img_y = 72, speed = 2):
    spawn = random.choice([0, 1, 7, 9, 30, 50, 80])
    image_queue = Queue()
    collision_queue = Queue()
    bp_lib = world.get_blueprint_library()
    # Get the required blueprints
    get_bp = 1
    vehicle_bp = bp_lib.filter('cybertruck')[0]
    camera_bp = bp_lib.filter('sensor.camera.rgb')[0]
    collision_bp = world.get_blueprint_library().find('sensor.other.collision')

    # # Configure the blueprints
    conf_bp = 1
    camera_bp.set_attribute("image_size_x", str(img_x))
    camera_bp.set_attribute("image_size_y", str(img_y))
    # Consider adding noise and blurring with enable_postprocess_effects

    # Spawn our actors
    spawn_actors = 1
    vehicle = world.spawn_actor(blueprint=vehicle_bp, transform=world.get_map().get_spawn_points()[spawn])

    camera = world.spawn_actor(blueprint=camera_bp, transform=carla.Transform(carla.Location(x=3.0, z=1.2)),
                               attach_to=vehicle)
    collision = world.spawn_actor(blueprint=collision_bp, transform=carla.Transform(), attach_to=vehicle)

    camera.listen(lambda data: sensor_callback(data, image_queue))
    collision.listen(lambda data: sensor_callback(data, collision_queue))

    tick_snapshot = 1
    world.tick()
    world.get_snapshot().frame

    speed_vec = 1
    speed_vec = carla.Vector3D(x=speed, y=0.0, z=0.0)
    vehicle.enable_constant_velocity(speed_vec)

    return vehicle, camera, collision, image_queue, collision_queue


# Send a command to the CARLA Simulator and collect data
def take_action(world, vehicle, image_queue, past_image, collision_queue, action):
    vehicle.apply_control(carla.VehicleControl(steer=action))
    world.tick()
    world.get_snapshot().frame

    # Ensure and image is returned
    try:
        image_data = image_queue.get(True, 1.0)
    except Empty:
        image_data = past_image
    
    # Determine if a collisions is observed
    try:
        collision_queue.get_nowait()
        collided = 1
    except Empty:
        collided = 0

    return image_data, collided

def close(world, camera, collision, vehicle, orig_settings):
    
    # Destroy the actors in the scene.
    if camera:
        camera.destroy()
    if vehicle:
        vehicle.destroy()
    if collision:
        collision.destroy()

# Create a stack of grayscale images.  If the image stakc is full pop the oldest one from the top and append a new one.
def preprocess_img(img, img_stack):
    img_array = np.copy(np.frombuffer(img.raw_data, dtype=np.dtype("uint8")))
    img_array = np.reshape(img_array, (img.height, img.width, 4))
    gray_img = cv2.cvtColor(img_array, cv2.COLOR_BGR2GRAY)

    if img_stack is None:
        img_stack = ((gray_img),) * 4
        img_stack = np.dstack(img_stack)
    else:
        img_stack = np.dstack((img_stack[:, :, 1:], gray_img))

    return img_stack