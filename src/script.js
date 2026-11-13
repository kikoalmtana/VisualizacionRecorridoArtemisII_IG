import * as THREE from "three";
import { OrbitControls } from "three/examples/jsm/controls/OrbitControls";
import GUI from "three/examples/jsm/libs/lil-gui.module.min.js";

let scene;
let camera;
let renderer;

let tierra;
let ejeTierra;

// Parametros físicos de la Tierra
const RADIO_TIERRA = 1;
const INCLINACION_AXIAL = THREE.MathUtils.degToRad(23.44);
const PERIODO_ROTACION = 86164;

// Parametros del reloj UTC
const reloj = new THREE.Clock();

const INICIO_MISION = Date.UTC(2026, 3, 2, 1, 58, 0);
const FIN_MISION = Date.UTC(2026, 3, 10, 23, 53, 0);

const DURACION_MISION = (FIN_MISION - INICIO_MISION) / 1000;

const estado = {
  t: 0,
  reproduciendo: false,
  velocidad: 1
};

let gui;
let botonPlay;

const informacion = {
  fechaUTC: "",
  tiempoMision: ""
};

function crearGUI() {

  gui = new GUI();

  // Posición centrada en la parte inferior
  gui.domElement.style.position = "fixed";
  gui.domElement.style.top = "auto";
  gui.domElement.style.left = "50%";
  gui.domElement.style.bottom = "10px";
  gui.domElement.style.transform = "translateX(-50%)";

  // Anchura del panel
  gui.domElement.style.width = "400px";
  gui.domElement.style.height = "180px";
  gui.domElement.style.maxWidth = "90vw";
  gui.domElement.style.boxSizing = "border-box";

  // Control del tiempo de simulación
  gui.add(estado, "t", 0, DURACION_MISION, 1)
    .name("Tiempo de misión")
    .listen();

  // Control de velocidad
  gui.add(estado, "velocidad", -10000, 100000, 0.5)
    .name("Velocidad");

  // Botón reproducir / pausar
  const acciones = {
    reproducirPausar: () => {
      estado.reproduciendo = !estado.reproduciendo;
    }
  };

  botonPlay = gui.add(acciones, "reproducirPausar")
    .name("Reproducir");

  // Información temporal
  const carpetaInfo = gui.addFolder("Información");

  carpetaInfo.add(informacion, "fechaUTC")
    .name("Fecha UTC")
    .listen()
    .disable();

  carpetaInfo.add(informacion, "tiempoMision")
    .name("Tiempo misión")
    .listen()
    .disable();

}

function actualizarGUI() {

  const fecha = new Date(INICIO_MISION + estado.t * 1000);

  // Fecha UTC
  informacion.fechaUTC = fecha.toISOString()
    .replace("T", " ")
    .replace(".000Z", " UTC");

  // Tiempo transcurrido de misión
  const tiempo = Math.floor(estado.t);

  const dias = Math.floor(tiempo / 86400);
  const horas = Math.floor((tiempo % 86400) / 3600);
  const minutos = Math.floor((tiempo % 3600) / 60);
  const segundos = tiempo % 60;

  informacion.tiempoMision =
    `T+${String(dias).padStart(2, "0")}:` +
    `${String(horas).padStart(2, "0")}:` +
    `${String(minutos).padStart(2, "0")}:` +
    `${String(segundos).padStart(2, "0")}`;

  // Actualizar el nombre del botón
  botonPlay.name(
    estado.reproduciendo ? "Pausar" : "Reproducir"
  );

}

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

  crearGUI();
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

function animationLoop() {

  requestAnimationFrame(animationLoop);

  const delta = reloj.getDelta();

  if (estado.reproduciendo) {

    estado.t += delta * estado.velocidad;

    estado.t = THREE.MathUtils.clamp(
      estado.t,
      0,
      DURACION_MISION
    );

    // Detener al alcanzar los extremos
    if (estado.t === 0 || estado.t === DURACION_MISION) {
      estado.reproduciendo = false;
    }
  }

  // Rotación terrestre según el tiempo absoluto
  tierra.rotation.y =
    (2 * Math.PI / PERIODO_ROTACION) * estado.t;

  actualizarGUI();

  renderer.render(scene, camera);
}