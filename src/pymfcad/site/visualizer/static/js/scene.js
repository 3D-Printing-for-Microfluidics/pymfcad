import * as THREE from "three";
import { RulerAxesHelper } from "./ruler.js";
import { OrbitControls } from "../../../static/js/controls/OrbitControls.js";
import { TrackballControls } from "../../../static/js/controls/TrackballControls.js";

export function createScene() {
  const scene = new THREE.Scene();

  const world = new THREE.Group();
  scene.add(world);
  world.rotation.x = -Math.PI / 2;

  // const axes = new THREE.AxesHelper(100);
  // axes.position.set(-0.0001, -0.0001, -0.0001);
  // world.add(axes);

  const perspectiveCamera = new THREE.PerspectiveCamera(
    20,
    window.innerWidth / window.innerHeight,
    0.1,
    1000,
  );
  const orthographicCamera = new THREE.OrthographicCamera(
    -1,
    1,
    1,
    -1,
    0.1,
    1000,
  );

  const renderer = new THREE.WebGLRenderer({ antialias: true });
  renderer.setSize(window.innerWidth, window.innerHeight);
  renderer.setPixelRatio(window.devicePixelRatio || 1);
  document.body.appendChild(renderer.domElement);
  renderer.domElement.setAttribute("tabindex", "0");
  renderer.domElement.style.outline = "none";
  renderer.domElement.addEventListener("pointerdown", () => {
    renderer.domElement.focus();
  });

  const axes = new RulerAxesHelper(100, perspectiveCamera, renderer);
  axes.position.set(-0.0001, -0.0001, -0.0001);
  world.add(axes);

  const orbitControls = new OrbitControls(
    perspectiveCamera,
    renderer.domElement,
  );
  orbitControls.enableDamping = true;
  orbitControls.dampingFactor = 0.08;
  if (typeof orbitControls.listenToKeyEvents === "function") {
    orbitControls.listenToKeyEvents(window);
  }

  const trackballControls = new TrackballControls(
    perspectiveCamera,
    renderer.domElement,
  );
  trackballControls.enabled = false;
  trackballControls.rotateSpeed = 4.0;
  trackballControls.zoomSpeed = 1.2;
  trackballControls.panSpeed = 0.3;
  trackballControls.staticMoving = false;
  trackballControls.dynamicDampingFactor = 0.2;

  let activeControls = orbitControls;

  function setControlsType(type) {
    const next = type === "trackball" ? trackballControls : orbitControls;
    if (next === activeControls) return activeControls;
    if (activeControls && activeControls.target && next.target) {
      next.target.copy(activeControls.target);
    }
    if (activeControls) {
      activeControls.enabled = false;
    }
    next.enabled = true;
    activeControls = next;
    return activeControls;
  }

  return {
    THREE,
    scene,
    world,
    axes,
    renderer,
    controls: activeControls,
    orbitControls,
    trackballControls,
    setControlsType,
    perspectiveCamera,
    orthographicCamera,
  };
}
