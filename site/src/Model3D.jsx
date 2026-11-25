// 3D viewer of a machine (GLB from tools/blender_export_glb.py). Loaded lazily: three.js is only fetched when a page
// shows a model.
import { Suspense, useEffect } from "react";
import { Canvas } from "@react-three/fiber";
import { OrbitControls, useGLTF, Bounds, ContactShadows, Environment, Lightformer } from "@react-three/drei";

function Model({ name }) {
  const { scene } = useGLTF(`/models/${name}.glb`);
  useEffect(() => {
    scene.traverse((o) => {
      if (o.isMesh) {
        o.castShadow = true;
        o.receiveShadow = true;
      }
    });
  }, [scene]);
  return <primitive object={scene} />;
}

export default function Model3D({ name, autoRotate = true, interactive = true }) {
  return (
    <Canvas shadows dpr={[1, 2]} camera={{ position: [2.6, 1.9, 2.6], fov: 35 }} gl={{ antialias: true }}>
      <color attach="background" args={["#11141a"]} />
      <hemisphereLight intensity={0.55} groundColor="#1a1208" color="#dfe7f2" />
      <directionalLight position={[4, 6, 3]} intensity={2.2} castShadow shadow-mapSize={[1024, 1024]} />
      <directionalLight position={[-4, 2, -3]} intensity={0.7} color="#f3c068" />
      <Environment resolution={128}>
        <Lightformer intensity={2} position={[0, 5, -6]} scale={[10, 3, 1]} />
        <Lightformer intensity={1.2} color="#f3c068" position={[-5, 1, 2]} scale={[3, 6, 1]} />
        <Lightformer intensity={0.8} color="#4cc3d9" position={[5, 1, 2]} scale={[3, 6, 1]} />
      </Environment>
      <Suspense fallback={null}>
        <Bounds fit clip observe margin={1.25} key={name}>
          <Model name={name} />
        </Bounds>
        <ContactShadows position={[0, -0.01, 0]} opacity={0.55} scale={6} blur={2.4} far={3} />
      </Suspense>
      <OrbitControls makeDefault autoRotate={autoRotate} autoRotateSpeed={0.8} enablePan={false} enableZoom={interactive}
                     minPolarAngle={0.2} maxPolarAngle={Math.PI / 2.05} />
    </Canvas>
  );
}
