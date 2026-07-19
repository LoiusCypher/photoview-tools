# docker run -it --volume $(pwd):/root/workdir --volume="/run/user/1000/$WAYLAND_DISPLAY:/tmp/runtime-root/$WAYLAND_DISPLAY:rw" --privileged 24d2e5c61ef981bcf8bc8e38630a2515fbc5c856459fa67d431875e1ac4eab02
#
# sudo is required
sudo docker compose -f docker-compose-labelme-python.yml build labelme
sudo docker compose -f docker-compose-labelme-python.yml run labelme

