import glob
import os
from pickle import TRUE
from queue import Queue
import matplotlib.pyplot as plt
import sys
import cv2

from zmq import QUEUE

try:
    sys.path.append(glob.glob('../PythonAPI/carla/dist/carla-*%d.%d-%s.egg' % (
        sys.version_info.major,
        sys.version_info.minor,
        'win-amd64' if os.name == 'nt' else 'linux-x86_64'))[0])
except IndexError:
    pass


import carla
from queue import Queue
from queue import Empty
from PIL import Image
import numpy as np

def sensor_callback(data, queue):
    """
    This simple callback just stores the data on a thread safe Python Queue
    to be retrieved from the "main thread".
    """
    queue.put(data)

def run_simulation(client):

    try:
        sim_time = 30
        time_step = 0.1
        
        # Get the world and its information
        world = client.get_world()
        bp_lib = world.get_blueprint_library()
        original_settings = world.get_settings()

        # Configure the world
        settings = world.get_settings()
        settings.synchronous_mode = True #make the server wait for the client
        settings.fixed_delta_seconds = time_step
        world.apply_settings(settings)
      
        vehicle = None
        camera = None
        collision = None
        
        # Get the required blueprints
        vehicle_bp = bp_lib.filter('cybertruck')[0]
        camera_bp = bp_lib.filter('sensor.camera.rgb')[0]
        collision_bp = world.get_blueprint_library().find('sensor.other.collision')

        # # Configure the blueprints
        camera_bp.set_attribute("image_size_x", '400')
        camera_bp.set_attribute("image_size_y", '300')
        # Consider adding noise and and blurring with enable_postprocess_effects
        
        

        # Spawn our actors
        vehicle = world.spawn_actor(blueprint=vehicle_bp, transform=world.get_map().get_spawn_points()[0])
        camera = world.spawn_actor(blueprint=camera_bp, transform=carla.Transform(carla.Location(x=3.0, z=1.2)), attach_to=vehicle)
        collision = world.spawn_actor(blueprint=collision_bp, transform=carla.Transform(), attach_to=vehicle)

        img_stack = []
        image_queue = Queue()
        camera.listen(lambda data: sensor_callback(data, image_queue))
        collision_queue = Queue()
        collision.listen(lambda data: sensor_callback(data, collision_queue))

        steering = 0
        steering_list=[0, 0.05, -0.05]
        #for step in range(int(sim_time/time_step)):
        for step in range(4):
            if (step+1)%25==0 and step > 100:
                # turn = not(turn)
                # if turn:
                #     right_turn = not(right_turn)
                vehicle.apply_control(carla.VehicleControl(throttle=0.2, steer=steering))
                steering = min(max(-0.10, steering + np.random.choice(steering_list, p=[1/3,1/3, 1-2/3])), 0.10)
            elif step <= 100:
                vehicle.apply_control(carla.VehicleControl(throttle=0.2, steer=steering))

            
            # if turn and right_turn:
            #     vehicle.apply_control(carla.VehicleControl(throttle=0.2, steer=0.5))
            # elif turn:
            #     vehicle.apply_control(carla.VehicleControl(throttle=0.2, steer=-0.5))
            # else:
            #     vehicle.apply_control(carla.VehicleControl(throttle=0.5, steer=0.0))
            

            world.tick()
            world_frame = world.get_snapshot().frame

        
            image_data = image_queue.get(True, 1.0)
            try:
                collision_data = collision_queue.get_nowait()
                collision_text = "Collision"
            except Empty:
                collision_text = "No Collision"

        
            #output information to the screen
            sys.stdout.write("\r(%d/%d) Simulation: %d Camera: %d " %
                (step+1, sim_time/time_step, world_frame, image_data.frame) + ' ' + collision_text + '    ')
            sys.stdout.flush()

            img_array = np.copy(np.frombuffer(image_data.raw_data, dtype=np.dtype("uint8")))
            img_array = np.reshape(img_array, (image_data.height, image_data.width, 4))
            gray_img = cv2.cvtColor(img_array, cv2.COLOR_BGR2GRAY)

            # cv2.imshow('Gray image', gray)
            # cv2.waitKey(0)
            # cv2.destroyAllWindows()
            
            cv2.imwrite("../output_data/%08d.png" % image_data.frame, gray_img)


      
    
    finally:
        # Apply the original settings when exiting.
        world.apply_settings(original_settings)

        # Destroy the actors in the scene.
        if camera:
            camera.destroy()
        if vehicle:
            vehicle.destroy()
        if collision:
            collision.destroy()



def main():
    
    try:
        client = carla.Client('localhost', 2000)
        client.set_timeout(10.0)
        run_simulation(client)
    
    except:
        print("Something went wrong.")

if __name__ == '__main__':

    main()
