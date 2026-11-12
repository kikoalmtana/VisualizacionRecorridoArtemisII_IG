import * as THREE from "three";
import { OrbitControls } from "three/examples/jsm/controls/OrbitControls";

let scene;
let camera;
let renderer;

let tierra;
let ejeTierra;
const reloj = new THREE.Clock();

// Parametros físicos de la Tierra
const RADIO_TIERRA = 1;
const INCLINACION_AXIAL = THREE.MathUtils.degToRad(23.44);
const PERIODO_ROTACION = 86164;
const TIME_SCALE = 3600;

const VEL_ROTACION = ((2 * Math.PI) / PERIODO_ROTACION) * TIME_SCALE;

init();
animationLoop();

function init() {
  var info = document.createElement("div");
  info.style.position = "absolute";
  info.style.top = "30px";
  info.style.width = "100%";
  info.style.textAlign = "center";
  info.style.color = "#fff";
  info.style.fontWeight = "bold";
  info.style.backgroundColor = "transparent";
  info.style.zIndex = "1";
  info.style.fontFamily = "Monospace";
  info.innerHTML = "Visualización recorrido Artemis II";
  document.body.appendChild(info);

  scene = new THREE.Scene();
  camera = new THREE.PerspectiveCamera(
    75,
    window.innerWidth / window.innerHeight,
    0.1,
    1000
  );
  camera.position.set(0, 1, 4);

  renderer = new THREE.WebGLRenderer({ antialias: true });
  renderer.setSize(window.innerWidth, window.innerHeight);
  document.body.appendChild(renderer.domElement);

  // Luces: el Sol (direccional) + un poco de ambiente para no ver negro total
  const sol = new THREE.DirectionalLight(0xffffff, 2.5);
  sol.position.set(10, 3, 5);
  scene.add(sol);
  scene.add(new THREE.AmbientLight(0xffffff, 0.15));

  //Objetos
  Tierra(RADIO_TIERRA, "./assets/earthmap1k.jpg");

  var controls = new OrbitControls(camera, renderer.domElement);
  controls.minDistance = RADIO_TIERRA * 1.2;
}

function Tierra(radio, rutaTextura) {
  const textura = new THREE.TextureLoader().load(rutaTextura);
  textura.colorSpace = THREE.SRGBColorSpace; // colores correctos

  const geometry = new THREE.SphereGeometry(radio, 64, 64);
  const material = new THREE.MeshPhongMaterial({
    map: textura,
    shininess: 5,
  });
  tierra = new THREE.Mesh(geometry, material);


  ejeTierra = new THREE.Object3D();
  ejeTierra.rotation.z = INCLINACION_AXIAL;
  ejeTierra.add(tierra);
  scene.add(ejeTierra);
}

//Bucle de animación
function animationLoop() {
  requestAnimationFrame(animationLoop);

  // Tiempo transcurrido entre fotogramas: la velocidad no depende de los FPS
  const delta = reloj.getDelta();

  // Rotación hacia el este (antihoraria vista desde el polo norte, +Y)
  tierra.rotation.y += VEL_ROTACION * delta;

  renderer.render(scene, camera);
}