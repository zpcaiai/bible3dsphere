var Bo=Object.defineProperty;var No=(n,t,e)=>t in n?Bo(n,t,{enumerable:!0,configurable:!0,writable:!0,value:e}):n[t]=e;var y=(n,t,e)=>No(n,typeof t!="symbol"?t+"":t,e);import{R as gt,S as Uo,a as H,g as Do,r as jo,b as Go,n as $o,T as Vo,c as Wo,d as Ho,W as me}from"./webgl-device-GdO2XAOk.js";import{a9 as ui,aa as Ko,c as P,a1 as R,p as Yo,O as Zo,ab as qo,ac as Xo,J as Jo,$ as Qo,ad as ts,ae as es,af as _n,ag as is,a0 as k,ah as xn,S as ns,ai as Ie,a6 as Ht,aj as ye,d as T,C as Z,ak as os,A as Xe,o as bn,al as ss,w as B,U as Ut,am as J,z as Et,an as Kt,ao as it,ap as q,aq as ve,ar as rt,L as rs,as,v as Oe,y as ls,at as G,_ as fi}from"./webgl-developer-tools-DgbUBCYU.js";import{$ as cs}from"./three-BaU7gAd8.js";function us(n){return ArrayBuffer.isView(n)&&!(n instanceof DataView)}function fs(n){return Array.isArray(n)?n.length===0||typeof n[0]=="number":!1}function ds(n){return us(n)||fs(n)}const hs=`out vec4 transform_output;
void main() {
  transform_output = vec4(0);
}`,ps=`#version 300 es
${hs}`;function gs(n){const{input:t,inputChannels:e,output:i}={};if(!t)return ps;if(!e)throw new Error("inputChannels");const o=ms(e),s=ys(t,e);return`#version 300 es
in ${o} ${t};
out vec4 ${i};
void main() {
  ${i} = ${s};
}`}function ms(n){switch(n){case 1:return"float";case 2:return"vec2";case 3:return"vec3";case 4:return"vec4";default:throw new Error(`invalid channels: ${n}`)}}function ys(n,t){switch(t){case 1:return`vec4(${n}, 0.0, 0.0, 1.0)`;case 2:return`vec4(${n}, 0.0, 1.0)`;case 3:return`vec4(${n}, 1.0)`;case 4:return n;default:throw new Error(`invalid channels: ${t}`)}}function Pn(n,t=[],e=0){const i=Math.fround(n),o=n-i;return t[e]=i,t[e+1]=o,t}function vs(n){return n-Math.fround(n)}function _s(n){const t=new Float32Array(32);for(let e=0;e<4;++e)for(let i=0;i<4;++i){const o=e*4+i;Pn(n[i*4+e],t,o*2)}return t}function Cn(n,t=!0){return n??t}function Ln(n=[0,0,0],t=!0){return t?n.map(e=>e/255):[...n]}function xs(n,t=!0){const e=Ln(n.slice(0,3),t),i=Number.isFinite(n[3]),o=i?n[3]:1;return[e[0],e[1],e[2],t&&i?o/255:o]}const di=`
layout(std140) uniform fp64arithmeticUniforms {
  uniform float ONE;
  uniform float SPLIT;
} fp64;

/*
About LUMA_FP64_CODE_ELIMINATION_WORKAROUND

The purpose of this workaround is to prevent shader compilers from
optimizing away necessary arithmetic operations by swapping their sequences
or transform the equation to some 'equivalent' form.

These helpers implement Dekker/Veltkamp-style error tracking. If the compiler
folds constants or reassociates the arithmetic, the high/low split can stop
tracking the rounding error correctly. That failure mode tends to look fine in
simple coordinate setup, but then breaks down inside iterative arithmetic such
as fp64 Mandelbrot loops.

The method is to multiply an artifical variable, ONE, which will be known to
the compiler to be 1 only at runtime. The whole expression is then represented
as a polynomial with respective to ONE. In the coefficients of all terms, only one a
and one b should appear

err = (a + b) * ONE^6 - a * ONE^5 - (a + b) * ONE^4 + a * ONE^3 - b - (a + b) * ONE^2 + a * ONE
*/

float prevent_fp64_optimization(float value) {
#if defined(LUMA_FP64_CODE_ELIMINATION_WORKAROUND)
  return value + fp64.ONE * 0.0;
#else
  return value;
#endif
}

// Divide float number to high and low floats to extend fraction bits
vec2 split(float a) {
  // Keep SPLIT as a runtime uniform so the compiler cannot fold the Dekker
  // split into a constant expression and reassociate the recovery steps.
  float split = prevent_fp64_optimization(fp64.SPLIT);
  float t = prevent_fp64_optimization(a * split);
  float temp = t - a;
  float a_hi = t - temp;
  float a_lo = a - a_hi;
  return vec2(a_hi, a_lo);
}

// Divide float number again when high float uses too many fraction bits
vec2 split2(vec2 a) {
  vec2 b = split(a.x);
  b.y += a.y;
  return b;
}

// Special sum operation when a > b
vec2 quickTwoSum(float a, float b) {
#if defined(LUMA_FP64_CODE_ELIMINATION_WORKAROUND)
  float sum = (a + b) * fp64.ONE;
  float err = b - (sum - a) * fp64.ONE;
#else
  float sum = a + b;
  float err = b - (sum - a);
#endif
  return vec2(sum, err);
}

// General sum operation
vec2 twoSum(float a, float b) {
  float s = (a + b);
#if defined(LUMA_FP64_CODE_ELIMINATION_WORKAROUND)
  float v = (s * fp64.ONE - a) * fp64.ONE;
  float err = (a - (s - v) * fp64.ONE) * fp64.ONE * fp64.ONE * fp64.ONE + (b - v);
#else
  float v = s - a;
  float err = (a - (s - v)) + (b - v);
#endif
  return vec2(s, err);
}

vec2 twoSub(float a, float b) {
  float s = (a - b);
#if defined(LUMA_FP64_CODE_ELIMINATION_WORKAROUND)
  float v = (s * fp64.ONE - a) * fp64.ONE;
  float err = (a - (s - v) * fp64.ONE) * fp64.ONE * fp64.ONE * fp64.ONE - (b + v);
#else
  float v = s - a;
  float err = (a - (s - v)) - (b + v);
#endif
  return vec2(s, err);
}

vec2 twoSqr(float a) {
  float prod = a * a;
  vec2 a_fp64 = split(a);
#if defined(LUMA_FP64_CODE_ELIMINATION_WORKAROUND)
  float err = ((a_fp64.x * a_fp64.x - prod) * fp64.ONE + 2.0 * a_fp64.x *
    a_fp64.y * fp64.ONE * fp64.ONE) + a_fp64.y * a_fp64.y * fp64.ONE * fp64.ONE * fp64.ONE;
#else
  float err = ((a_fp64.x * a_fp64.x - prod) + 2.0 * a_fp64.x * a_fp64.y) + a_fp64.y * a_fp64.y;
#endif
  return vec2(prod, err);
}

vec2 twoProd(float a, float b) {
  float prod = a * b;
  vec2 a_fp64 = split(a);
  vec2 b_fp64 = split(b);
  // twoProd is especially sensitive because mul_fp64 and div_fp64 both depend
  // on the split terms and cross terms staying in the original evaluation
  // order. If the compiler folds or reassociates them, the low part tends to
  // collapse to zero or NaN on some drivers.
  float highProduct = prevent_fp64_optimization(a_fp64.x * b_fp64.x);
  float crossProduct1 = prevent_fp64_optimization(a_fp64.x * b_fp64.y);
  float crossProduct2 = prevent_fp64_optimization(a_fp64.y * b_fp64.x);
  float lowProduct = prevent_fp64_optimization(a_fp64.y * b_fp64.y);
#if defined(LUMA_FP64_CODE_ELIMINATION_WORKAROUND)
  float err1 = (highProduct - prod) * fp64.ONE;
  float err2 = crossProduct1 * fp64.ONE * fp64.ONE;
  float err3 = crossProduct2 * fp64.ONE * fp64.ONE * fp64.ONE;
  float err4 = lowProduct * fp64.ONE * fp64.ONE * fp64.ONE * fp64.ONE;
#else
  float err1 = highProduct - prod;
  float err2 = crossProduct1;
  float err3 = crossProduct2;
  float err4 = lowProduct;
#endif
  float err = ((err1 + err2) + err3) + err4;
  return vec2(prod, err);
}

vec2 sum_fp64(vec2 a, vec2 b) {
  vec2 s, t;
  s = twoSum(a.x, b.x);
  t = twoSum(a.y, b.y);
  s.y += t.x;
  s = quickTwoSum(s.x, s.y);
  s.y += t.y;
  s = quickTwoSum(s.x, s.y);
  return s;
}

vec2 sub_fp64(vec2 a, vec2 b) {
  vec2 s, t;
  s = twoSub(a.x, b.x);
  t = twoSub(a.y, b.y);
  s.y += t.x;
  s = quickTwoSum(s.x, s.y);
  s.y += t.y;
  s = quickTwoSum(s.x, s.y);
  return s;
}

vec2 mul_fp64(vec2 a, vec2 b) {
  vec2 prod = twoProd(a.x, b.x);
  // y component is for the error
  prod.y += a.x * b.y;
#if defined(LUMA_FP64_HIGH_BITS_OVERFLOW_WORKAROUND)
  prod = split2(prod);
#endif
  prod = quickTwoSum(prod.x, prod.y);
  prod.y += a.y * b.x;
#if defined(LUMA_FP64_HIGH_BITS_OVERFLOW_WORKAROUND)
  prod = split2(prod);
#endif
  prod = quickTwoSum(prod.x, prod.y);
  return prod;
}

vec2 div_fp64(vec2 a, vec2 b) {
  float xn = 1.0 / b.x;
#if defined(LUMA_FP64_HIGH_BITS_OVERFLOW_WORKAROUND)
  vec2 yn = mul_fp64(a, vec2(xn, 0));
#else
  vec2 yn = a * xn;
#endif
  float diff = (sub_fp64(a, mul_fp64(b, yn))).x;
  vec2 prod = twoProd(xn, diff);
  return sum_fp64(yn, prod);
}

vec2 sqrt_fp64(vec2 a) {
  if (a.x == 0.0 && a.y == 0.0) return vec2(0.0, 0.0);
  if (a.x < 0.0) return vec2(0.0 / 0.0, 0.0 / 0.0);

  float x = 1.0 / sqrt(a.x);
  float yn = a.x * x;
#if defined(LUMA_FP64_CODE_ELIMINATION_WORKAROUND)
  vec2 yn_sqr = twoSqr(yn) * fp64.ONE;
#else
  vec2 yn_sqr = twoSqr(yn);
#endif
  float diff = sub_fp64(a, yn_sqr).x;
  vec2 prod = twoProd(x * 0.5, diff);
#if defined(LUMA_FP64_HIGH_BITS_OVERFLOW_WORKAROUND)
  return sum_fp64(split(yn), prod);
#else
  return sum_fp64(vec2(yn, 0.0), prod);
#endif
}
`,bs=`struct Fp64ArithmeticUniforms {
  ONE: f32,
  SPLIT: f32,
};

@group(0) @binding(auto) var<uniform> fp64arithmetic : Fp64ArithmeticUniforms;

fn fp64_nan(seed: f32) -> f32 {
  let nanBits = 0x7fc00000u | select(0u, 1u, seed < 0.0);
  return bitcast<f32>(nanBits);
}

fn fp64_runtime_zero() -> f32 {
  return fp64arithmetic.ONE * 0.0;
}

fn prevent_fp64_optimization(value: f32) -> f32 {
#ifdef LUMA_FP64_CODE_ELIMINATION_WORKAROUND
  return value + fp64_runtime_zero();
#else
  return value;
#endif
}

fn split(a: f32) -> vec2f {
  let splitValue = prevent_fp64_optimization(fp64arithmetic.SPLIT + fp64_runtime_zero());
  let t = prevent_fp64_optimization(a * splitValue);
  let temp = prevent_fp64_optimization(t - a);
  let aHi = prevent_fp64_optimization(t - temp);
  let aLo = prevent_fp64_optimization(a - aHi);
  return vec2f(aHi, aLo);
}

fn split2(a: vec2f) -> vec2f {
  var b = split(a.x);
  b.y = b.y + a.y;
  return b;
}

fn quickTwoSum(a: f32, b: f32) -> vec2f {
#ifdef LUMA_FP64_CODE_ELIMINATION_WORKAROUND
  let sum = prevent_fp64_optimization((a + b) * fp64arithmetic.ONE);
  let err = prevent_fp64_optimization(b - (sum - a) * fp64arithmetic.ONE);
#else
  let sum = prevent_fp64_optimization(a + b);
  let err = prevent_fp64_optimization(b - (sum - a));
#endif
  return vec2f(sum, err);
}

fn twoSum(a: f32, b: f32) -> vec2f {
  let s = prevent_fp64_optimization(a + b);
#ifdef LUMA_FP64_CODE_ELIMINATION_WORKAROUND
  let v = prevent_fp64_optimization((s * fp64arithmetic.ONE - a) * fp64arithmetic.ONE);
  let err =
    prevent_fp64_optimization((a - (s - v) * fp64arithmetic.ONE) *
      fp64arithmetic.ONE *
      fp64arithmetic.ONE *
      fp64arithmetic.ONE) +
    prevent_fp64_optimization(b - v);
#else
  let v = prevent_fp64_optimization(s - a);
  let err = prevent_fp64_optimization(a - (s - v)) + prevent_fp64_optimization(b - v);
#endif
  return vec2f(s, err);
}

fn twoSub(a: f32, b: f32) -> vec2f {
  let s = prevent_fp64_optimization(a - b);
#ifdef LUMA_FP64_CODE_ELIMINATION_WORKAROUND
  let v = prevent_fp64_optimization((s * fp64arithmetic.ONE - a) * fp64arithmetic.ONE);
  let err =
    prevent_fp64_optimization((a - (s - v) * fp64arithmetic.ONE) *
      fp64arithmetic.ONE *
      fp64arithmetic.ONE *
      fp64arithmetic.ONE) -
    prevent_fp64_optimization(b + v);
#else
  let v = prevent_fp64_optimization(s - a);
  let err = prevent_fp64_optimization(a - (s - v)) - prevent_fp64_optimization(b + v);
#endif
  return vec2f(s, err);
}

fn twoSqr(a: f32) -> vec2f {
  let prod = prevent_fp64_optimization(a * a);
  let aFp64 = split(a);
  let highProduct = prevent_fp64_optimization(aFp64.x * aFp64.x);
  let crossProduct = prevent_fp64_optimization(2.0 * aFp64.x * aFp64.y);
  let lowProduct = prevent_fp64_optimization(aFp64.y * aFp64.y);
#ifdef LUMA_FP64_CODE_ELIMINATION_WORKAROUND
  let err =
    (prevent_fp64_optimization(highProduct - prod) * fp64arithmetic.ONE +
      crossProduct * fp64arithmetic.ONE * fp64arithmetic.ONE) +
    lowProduct * fp64arithmetic.ONE * fp64arithmetic.ONE * fp64arithmetic.ONE;
#else
  let err = ((prevent_fp64_optimization(highProduct - prod) + crossProduct) + lowProduct);
#endif
  return vec2f(prod, err);
}

fn twoProd(a: f32, b: f32) -> vec2f {
  let prod = prevent_fp64_optimization(a * b);
  let aFp64 = split(a);
  let bFp64 = split(b);
  let highProduct = prevent_fp64_optimization(aFp64.x * bFp64.x);
  let crossProduct1 = prevent_fp64_optimization(aFp64.x * bFp64.y);
  let crossProduct2 = prevent_fp64_optimization(aFp64.y * bFp64.x);
  let lowProduct = prevent_fp64_optimization(aFp64.y * bFp64.y);
#ifdef LUMA_FP64_CODE_ELIMINATION_WORKAROUND
  let err1 = (highProduct - prod) * fp64arithmetic.ONE;
  let err2 = crossProduct1 * fp64arithmetic.ONE * fp64arithmetic.ONE;
  let err3 = crossProduct2 * fp64arithmetic.ONE * fp64arithmetic.ONE * fp64arithmetic.ONE;
  let err4 =
    lowProduct *
    fp64arithmetic.ONE *
    fp64arithmetic.ONE *
    fp64arithmetic.ONE *
    fp64arithmetic.ONE;
#else
  let err1 = highProduct - prod;
  let err2 = crossProduct1;
  let err3 = crossProduct2;
  let err4 = lowProduct;
#endif
  let err12InputA = prevent_fp64_optimization(err1);
  let err12InputB = prevent_fp64_optimization(err2);
  let err12 = prevent_fp64_optimization(err12InputA + err12InputB);
  let err123InputA = prevent_fp64_optimization(err12);
  let err123InputB = prevent_fp64_optimization(err3);
  let err123 = prevent_fp64_optimization(err123InputA + err123InputB);
  let err1234InputA = prevent_fp64_optimization(err123);
  let err1234InputB = prevent_fp64_optimization(err4);
  let err = prevent_fp64_optimization(err1234InputA + err1234InputB);
  return vec2f(prod, err);
}

fn sum_fp64(a: vec2f, b: vec2f) -> vec2f {
  var s = twoSum(a.x, b.x);
  let t = twoSum(a.y, b.y);
  s.y = prevent_fp64_optimization(s.y + t.x);
  s = quickTwoSum(s.x, s.y);
  s.y = prevent_fp64_optimization(s.y + t.y);
  s = quickTwoSum(s.x, s.y);
  return s;
}

fn sub_fp64(a: vec2f, b: vec2f) -> vec2f {
  var s = twoSub(a.x, b.x);
  let t = twoSub(a.y, b.y);
  s.y = prevent_fp64_optimization(s.y + t.x);
  s = quickTwoSum(s.x, s.y);
  s.y = prevent_fp64_optimization(s.y + t.y);
  s = quickTwoSum(s.x, s.y);
  return s;
}

fn mul_fp64(a: vec2f, b: vec2f) -> vec2f {
  var prod = twoProd(a.x, b.x);
  let crossProduct1 = prevent_fp64_optimization(a.x * b.y);
  prod.y = prevent_fp64_optimization(prod.y + crossProduct1);
#ifdef LUMA_FP64_HIGH_BITS_OVERFLOW_WORKAROUND
  prod = split2(prod);
#endif
  prod = quickTwoSum(prod.x, prod.y);
  let crossProduct2 = prevent_fp64_optimization(a.y * b.x);
  prod.y = prevent_fp64_optimization(prod.y + crossProduct2);
#ifdef LUMA_FP64_HIGH_BITS_OVERFLOW_WORKAROUND
  prod = split2(prod);
#endif
  prod = quickTwoSum(prod.x, prod.y);
  return prod;
}

fn div_fp64(a: vec2f, b: vec2f) -> vec2f {
  let xn = prevent_fp64_optimization(1.0 / b.x);
  let yn = mul_fp64(a, vec2f(xn, fp64_runtime_zero()));
  let diff = prevent_fp64_optimization(sub_fp64(a, mul_fp64(b, yn)).x);
  let prod = twoProd(xn, diff);
  return sum_fp64(yn, prod);
}

fn sqrt_fp64(a: vec2f) -> vec2f {
  if (a.x == 0.0 && a.y == 0.0) {
    return vec2f(0.0, 0.0);
  }
  if (a.x < 0.0) {
    let nanValue = fp64_nan(a.x);
    return vec2f(nanValue, nanValue);
  }

  let x = prevent_fp64_optimization(1.0 / sqrt(a.x));
  let yn = prevent_fp64_optimization(a.x * x);
#ifdef LUMA_FP64_CODE_ELIMINATION_WORKAROUND
  let ynSqr = twoSqr(yn) * fp64arithmetic.ONE;
#else
  let ynSqr = twoSqr(yn);
#endif
  let diff = prevent_fp64_optimization(sub_fp64(a, ynSqr).x);
  let prod = twoProd(prevent_fp64_optimization(x * 0.5), diff);
#ifdef LUMA_FP64_HIGH_BITS_OVERFLOW_WORKAROUND
  return sum_fp64(split(yn), prod);
#else
  return sum_fp64(vec2f(yn, 0.0), prod);
#endif
}
`,Ps={ONE:1,SPLIT:4097},Cs={name:"fp64arithmetic",source:bs,fs:di,vs:di,defaultUniforms:Ps,uniformTypes:{ONE:"f32",SPLIT:"f32"},fp64ify:Pn,fp64LowPart:vs,fp64ifyMatrix4:_s},hi=`layout(std140) uniform floatColorsUniforms {
  float useByteColors;
} floatColors;

vec3 floatColors_normalize(vec3 inputColor) {
  return floatColors.useByteColors > 0.5 ? inputColor / 255.0 : inputColor;
}

vec4 floatColors_normalize(vec4 inputColor) {
  return floatColors.useByteColors > 0.5 ? inputColor / 255.0 : inputColor;
}

vec4 floatColors_premultiplyAlpha(vec4 inputColor) {
  return vec4(inputColor.rgb * inputColor.a, inputColor.a);
}

vec4 floatColors_unpremultiplyAlpha(vec4 inputColor) {
  return inputColor.a > 0.0 ? vec4(inputColor.rgb / inputColor.a, inputColor.a) : vec4(0.0);
}

vec4 floatColors_premultiply_alpha(vec4 inputColor) {
  return floatColors_premultiplyAlpha(inputColor);
}

vec4 floatColors_unpremultiply_alpha(vec4 inputColor) {
  return floatColors_unpremultiplyAlpha(inputColor);
}
`,Ls=`struct floatColorsUniforms {
  useByteColors: f32
};

@group(0) @binding(auto) var<uniform> floatColors : floatColorsUniforms;

fn floatColors_normalize(inputColor: vec3<f32>) -> vec3<f32> {
  return select(inputColor, inputColor / 255.0, floatColors.useByteColors > 0.5);
}

fn floatColors_normalize4(inputColor: vec4<f32>) -> vec4<f32> {
  return select(inputColor, inputColor / 255.0, floatColors.useByteColors > 0.5);
}

fn floatColors_premultiplyAlpha(inputColor: vec4<f32>) -> vec4<f32> {
  return vec4<f32>(inputColor.rgb * inputColor.a, inputColor.a);
}

fn floatColors_unpremultiplyAlpha(inputColor: vec4<f32>) -> vec4<f32> {
  return select(
    vec4<f32>(0.0),
    vec4<f32>(inputColor.rgb / inputColor.a, inputColor.a),
    inputColor.a > 0.0
  );
}

fn floatColors_premultiply_alpha(inputColor: vec4<f32>) -> vec4<f32> {
  return floatColors_premultiplyAlpha(inputColor);
}

fn floatColors_unpremultiply_alpha(inputColor: vec4<f32>) -> vec4<f32> {
  return floatColors_unpremultiplyAlpha(inputColor);
}
`,wn={name:"floatColors",props:{},uniforms:{},vs:hi,fs:hi,source:Ls,uniformTypes:{useByteColors:"f32"},defaultUniforms:{useByteColors:!0}},ws=[0,1,1,1],As=`layout(std140) uniform pickingUniforms {
  float isActive;
  float isAttribute;
  float isHighlightActive;
  float useByteColors;
  vec3 highlightedObjectColor;
  vec4 highlightColor;
} picking;

out vec4 picking_vRGBcolor_Avalid;

// Normalize unsigned byte color to 0-1 range
vec3 picking_normalizeColor(vec3 color) {
  return picking.useByteColors > 0.5 ? color / 255.0 : color;
}

// Normalize unsigned byte color to 0-1 range
vec4 picking_normalizeColor(vec4 color) {
  return picking.useByteColors > 0.5 ? color / 255.0 : color;
}

bool picking_isColorZero(vec3 color) {
  return dot(color, vec3(1.0)) < 0.00001;
}

bool picking_isColorValid(vec3 color) {
  return dot(color, vec3(1.0)) > 0.00001;
}

// Check if this vertex is highlighted 
bool isVertexHighlighted(vec3 vertexColor) {
  vec3 highlightedObjectColor = picking_normalizeColor(picking.highlightedObjectColor);
  return
    bool(picking.isHighlightActive) && picking_isColorZero(abs(vertexColor - highlightedObjectColor));
}

// Set the current picking color
void picking_setPickingColor(vec3 pickingColor) {
  pickingColor = picking_normalizeColor(pickingColor);

  if (bool(picking.isActive)) {
    // Use alpha as the validity flag. If pickingColor is [0, 0, 0] fragment is non-pickable
    picking_vRGBcolor_Avalid.a = float(picking_isColorValid(pickingColor));

    if (!bool(picking.isAttribute)) {
      // Stores the picking color so that the fragment shader can render it during picking
      picking_vRGBcolor_Avalid.rgb = pickingColor;
    }
  } else {
    // Do the comparison with selected item color in vertex shader as it should mean fewer compares
    picking_vRGBcolor_Avalid.a = float(isVertexHighlighted(pickingColor));
  }
}

void picking_setPickingAttribute(float value) {
  if (bool(picking.isAttribute)) {
    picking_vRGBcolor_Avalid.r = value;
  }
}

void picking_setPickingAttribute(vec2 value) {
  if (bool(picking.isAttribute)) {
    picking_vRGBcolor_Avalid.rg = value;
  }
}

void picking_setPickingAttribute(vec3 value) {
  if (bool(picking.isAttribute)) {
    picking_vRGBcolor_Avalid.rgb = value;
  }
}
`,Ss=`layout(std140) uniform pickingUniforms {
  float isActive;
  float isAttribute;
  float isHighlightActive;
  float useByteColors;
  vec3 highlightedObjectColor;
  vec4 highlightColor;
} picking;

in vec4 picking_vRGBcolor_Avalid;

/*
 * Returns highlight color if this item is selected.
 */
vec4 picking_filterHighlightColor(vec4 color) {
  // If we are still picking, we don't highlight
  if (picking.isActive > 0.5) {
    return color;
  }

  bool selected = bool(picking_vRGBcolor_Avalid.a);

  if (selected) {
    // Blend in highlight color based on its alpha value
    float highLightAlpha = picking.highlightColor.a;
    float blendedAlpha = highLightAlpha + color.a * (1.0 - highLightAlpha);
    float highLightRatio = highLightAlpha / blendedAlpha;

    vec3 blendedRGB = mix(color.rgb, picking.highlightColor.rgb, highLightRatio);
    return vec4(blendedRGB, blendedAlpha);
  } else {
    return color;
  }
}

/*
 * Returns picking color if picking enabled else unmodified argument.
 */
vec4 picking_filterPickingColor(vec4 color) {
  if (bool(picking.isActive)) {
    if (picking_vRGBcolor_Avalid.a == 0.0) {
      discard;
    }
    return picking_vRGBcolor_Avalid;
  }
  return color;
}

/*
 * Returns picking color if picking is enabled if not
 * highlight color if this item is selected, otherwise unmodified argument.
 */
vec4 picking_filterColor(vec4 color) {
  vec4 highlightColor = picking_filterHighlightColor(color);
  return picking_filterPickingColor(highlightColor);
}
`,pi={props:{},uniforms:{},name:"picking",uniformTypes:{isActive:"f32",isAttribute:"f32",isHighlightActive:"f32",useByteColors:"f32",highlightedObjectColor:"vec3<f32>",highlightColor:"vec4<f32>"},defaultUniforms:{isActive:!1,isAttribute:!1,isHighlightActive:!1,useByteColors:!0,highlightedObjectColor:[0,0,0],highlightColor:ws},vs:As,fs:Ss,getUniforms:Ts};function Ts(n={},t){const e={},i=Cn(n.useByteColors,!0);if(n.highlightedObjectColor!==void 0)if(n.highlightedObjectColor===null)e.isHighlightActive=!1;else{e.isHighlightActive=!0;const o=n.highlightedObjectColor.slice(0,3);e.highlightedObjectColor=o}return n.highlightColor&&(e.highlightColor=xs(n.highlightColor,i)),n.isActive!==void 0&&(e.isActive=!!n.isActive,e.isAttribute=!!n.isAttribute),n.useByteColors!==void 0&&(e.useByteColors=!!n.useByteColors),e}const ee=class ee extends ui{constructor(e,i){super(e,i,ee.defaultProps);y(this,"hash","");y(this,"shaderLayout");this.shaderLayout=i.shaderLayout}get[Symbol.toStringTag](){return"ComputePipeline"}};y(ee,"defaultProps",{...ui.defaultProps,shader:void 0,entryPoint:void 0,constants:{},shaderLayout:void 0});let Yt=ee;const ie=class ie{constructor(t){y(this,"device");y(this,"_hashCounter",0);y(this,"_hashes",{});y(this,"_renderPipelineCache",{});y(this,"_computePipelineCache",{});y(this,"_sharedRenderPipelineCache",{});this.device=t}static getDefaultPipelineFactory(t){const e=t.getModuleData("@luma.gl/core");return e.defaultPipelineFactory||(e.defaultPipelineFactory=new ie(t)),e.defaultPipelineFactory}get[Symbol.toStringTag](){return"PipelineFactory"}toString(){return`PipelineFactory(${this.device.id})`}createRenderPipeline(t){var r;if(!this.device.props._cachePipelines)return this.device.createRenderPipeline(t);const e={...gt.defaultProps,...t},i=this._renderPipelineCache,o=this._hashRenderPipeline(e);let s=(r=i[o])==null?void 0:r.resource;if(s)i[o].useCount++,this.device.props.debugFactories&&P.log(3,`${this}: ${i[o].resource} reused, count=${i[o].useCount}, (id=${t.id})`)();else{const a=this.device.type==="webgl"&&this.device.props._sharePipelines?this.createSharedRenderPipeline(e):void 0;s=this.device.createRenderPipeline({...e,id:e.id?`${e.id}-cached`:Ko("unnamed-cached"),_sharedRenderPipeline:a}),s.hash=o,i[o]={resource:s,useCount:1},this.device.props.debugFactories&&P.log(3,`${this}: ${s} created, count=${i[o].useCount}`)()}return s}createComputePipeline(t){var r;if(!this.device.props._cachePipelines)return this.device.createComputePipeline(t);const e={...Yt.defaultProps,...t},i=this._computePipelineCache,o=this._hashComputePipeline(e);let s=(r=i[o])==null?void 0:r.resource;return s?(i[o].useCount++,this.device.props.debugFactories&&P.log(3,`${this}: ${i[o].resource} reused, count=${i[o].useCount}, (id=${t.id})`)()):(s=this.device.createComputePipeline({...e,id:e.id?`${e.id}-cached`:void 0}),s.hash=o,i[o]={resource:s,useCount:1},this.device.props.debugFactories&&P.log(3,`${this}: ${s} created, count=${i[o].useCount}`)()),s}release(t){if(!this.device.props._cachePipelines){t.destroy();return}const e=this._getCache(t),i=t.hash;e[i].useCount--,e[i].useCount===0?(this._destroyPipeline(t),this.device.props.debugFactories&&P.log(3,`${this}: ${t} released and destroyed`)()):e[i].useCount<0?(P.error(`${this}: ${t} released, useCount < 0, resetting`)(),e[i].useCount=0):this.device.props.debugFactories&&P.log(3,`${this}: ${t} released, count=${e[i].useCount}`)()}createSharedRenderPipeline(t){const e=this._hashSharedRenderPipeline(t);let i=this._sharedRenderPipelineCache[e];return i||(i={resource:this.device._createSharedRenderPipelineWebGL(t),useCount:0},this._sharedRenderPipelineCache[e]=i),i.useCount++,i.resource}releaseSharedRenderPipeline(t){if(!t.sharedRenderPipeline)return;const e=this._hashSharedRenderPipeline(t.sharedRenderPipeline.props),i=this._sharedRenderPipelineCache[e];i&&(i.useCount--,i.useCount===0&&(i.resource.destroy(),delete this._sharedRenderPipelineCache[e]))}_destroyPipeline(t){const e=this._getCache(t);return this.device.props._destroyPipelines?(delete e[t.hash],t.destroy(),t instanceof gt&&this.releaseSharedRenderPipeline(t),!0):!1}_getCache(t){let e;if(t instanceof Yt&&(e=this._computePipelineCache),t instanceof gt&&(e=this._renderPipelineCache),!e)throw new Error(`${this}`);if(!e[t.hash])throw new Error(`${this}: ${t} matched incorrect entry`);return e}_hashComputePipeline(t){const{type:e}=this.device,i=this._getHash(t.shader.source),o=this._getHash(JSON.stringify(t.shaderLayout));return`${e}/C/${i}SL${o}`}_hashRenderPipeline(t){const e=t.vs?this._getHash(t.vs.source):0,i=t.fs?this._getHash(t.fs.source):0,o=this._getWebGLVaryingHash(t),s=this._getHash(JSON.stringify(t.shaderLayout)),r=this._getHash(JSON.stringify(t.bufferLayout)),{type:a}=this.device;switch(a){case"webgl":const l=this._getHash(JSON.stringify(t.parameters));return`${a}/R/${e}/${i}V${o}T${t.topology}P${l}SL${s}BL${r}`;case"webgpu":default:const c=this._getHash(JSON.stringify({vertexEntryPoint:t.vertexEntryPoint,fragmentEntryPoint:t.fragmentEntryPoint})),u=this._getHash(JSON.stringify(t.parameters)),f=this._getWebGPUAttachmentHash(t);return`${a}/R/${e}/${i}V${o}T${t.topology}EP${c}P${u}SL${s}BL${r}A${f}`}}_hashSharedRenderPipeline(t){const e=t.vs?this._getHash(t.vs.source):0,i=t.fs?this._getHash(t.fs.source):0,o=this._getWebGLVaryingHash(t);return`webgl/S/${e}/${i}V${o}`}_getHash(t){return this._hashes[t]===void 0&&(this._hashes[t]=this._hashCounter++),this._hashes[t]}_getWebGLVaryingHash(t){const{varyings:e=[],bufferMode:i=null}=t;return this._getHash(JSON.stringify({varyings:e,bufferMode:i}))}_getWebGPUAttachmentHash(t){var o;const e=t.colorAttachmentFormats??[this.device.preferredColorFormat],i=(o=t.parameters)!=null&&o.depthWriteEnabled?t.depthStencilAttachmentFormat||this.device.preferredDepthFormat:null;return this._getHash(JSON.stringify({colorAttachmentFormats:e,depthStencilAttachmentFormat:i}))}};y(ie,"defaultProps",{...gt.defaultProps});let Me=ie;const ne=class ne{constructor(t){y(this,"device");y(this,"_cache",{});this.device=t}static getDefaultShaderFactory(t){const e=t.getModuleData("@luma.gl/core");return e.defaultShaderFactory||(e.defaultShaderFactory=new ne(t)),e.defaultShaderFactory}get[Symbol.toStringTag](){return"ShaderFactory"}toString(){return`${this[Symbol.toStringTag]}(${this.device.id})`}createShader(t){if(!this.device.props._cacheShaders)return this.device.createShader(t);const e=this._hashShader(t);let i=this._cache[e];if(i)i.useCount++,this.device.props.debugFactories&&P.log(3,`${this}: Reusing shader ${i.resource.id} count=${i.useCount}`)();else{const o=this.device.createShader({...t,id:t.id?`${t.id}-cached`:void 0});this._cache[e]=i={resource:o,useCount:1},this.device.props.debugFactories&&P.log(3,`${this}: Created new shader ${o.id}`)()}return i.resource}release(t){if(!this.device.props._cacheShaders){t.destroy();return}const e=this._hashShader(t),i=this._cache[e];if(i)if(i.useCount--,i.useCount===0)this.device.props._destroyShaders&&(delete this._cache[e],i.resource.destroy(),this.device.props.debugFactories&&P.log(3,`${this}: Releasing shader ${t.id}, destroyed`)());else{if(i.useCount<0)throw new Error(`ShaderFactory: Shader ${t.id} released too many times`);this.device.props.debugFactories&&P.log(3,`${this}: Releasing shader ${t.id} count=${i.useCount}`)()}}_hashShader(t){return`${t.stage}:${t.source}`}};y(ne,"defaultProps",{...Uo.defaultProps});let Re=ne;function Es(n,t={}){const e={...n},i=t.layout??"std140",o={};let s=0;for(const[r,a]of Object.entries(e))s=ze(o,r,a,s,i);return s=H(s,Q(e,i)),{layout:i,byteLength:s*4,uniformTypes:e,fields:o}}function re(n,t){const e=jo(n),i=Do(e),o=/^mat(\d)x(\d)<.+>$/.exec(e);if(o){const r=Number(o[1]),a=Number(o[2]),l=gi(a,e,i.type),c=Os(l.size,l.alignment,t);return{alignment:l.alignment,size:r*c,components:r*a,columns:r,rows:a,columnStride:c,shaderType:e,type:i.type}}const s=/^vec(\d)<.+>$/.exec(e);return s?gi(Number(s[1]),e,i.type):{alignment:1,size:1,components:1,columns:1,rows:1,columnStride:1,shaderType:e,type:i.type}}function An(n){return!!n&&typeof n=="object"&&!Array.isArray(n)}function ze(n,t,e,i,o){if(typeof e=="string"){const s=re(e,o),r=H(i,s.alignment);return n[t]={offset:r,...s},r+s.size}if(Array.isArray(e)){if(Array.isArray(e[0]))throw new Error(`Nested arrays are not supported for ${t}`);const s=e[0],r=e[1],a=Tn(s,o),l=H(i,Q(e,o));for(let c=0;c<r;c++)ze(n,`${t}[${c}]`,s,l+c*a,o);return l+a*r}if(An(e)){const s=Q(e,o);let r=H(i,s);for(const[a,l]of Object.entries(e))r=ze(n,`${t}.${a}`,l,r,o);return H(r,s)}throw new Error(`Unsupported CompositeShaderType for ${t}`)}function Sn(n,t){if(typeof n=="string")return re(n,t).size;if(Array.isArray(n)){const i=n[0],o=n[1];if(Array.isArray(i))throw new Error("Nested arrays are not supported");return Tn(i,t)*o}let e=0;for(const i of Object.values(n)){const o=i;e=H(e,Q(o,t)),e+=Sn(o,t)}return H(e,Q(n,t))}function Q(n,t){if(typeof n=="string")return re(n,t).alignment;if(Array.isArray(n)){const i=n[0],o=Q(i,t);return En(t)?Math.max(o,4):o}let e=1;for(const i of Object.values(n)){const o=Q(i,t);e=Math.max(e,o)}return Ms(t)?Math.max(e,4):e}function gi(n,t,e,i){return{alignment:n===2?2:4,size:n===3?3:n,components:n,columns:1,rows:n,columnStride:n===3?3:n,shaderType:t,type:e}}function Tn(n,t){const e=Sn(n,t),i=Q(n,t);return Is(e,i,t)}function Is(n,t,e){return H(n,En(e)?4:t)}function Os(n,t,e){return e==="std140"?4:H(n,t)}function En(n){return n==="std140"||n==="wgsl-uniform"}function Ms(n){return n==="std140"||n==="wgsl-uniform"}function Rs(n){return ArrayBuffer.isView(n)&&!(n instanceof DataView)}function Zt(n){return Array.isArray(n)?n.length===0||typeof n[0]=="number":Rs(n)}class zs{constructor(t){y(this,"layout");this.layout=t}has(t){return!!this.layout.fields[t]}get(t){const e=this.layout.fields[t];return e?{offset:e.offset,size:e.size}:void 0}getFlatUniformValues(t){const e={};for(const[i,o]of Object.entries(t)){const s=this.layout.uniformTypes[i];s?this._flattenCompositeValue(e,i,s,o):this.layout.fields[i]&&(e[i]=o)}return e}getData(t){const e=Go(this.layout.byteLength);new Uint8Array(e,0,this.layout.byteLength).fill(0);const i={i32:new Int32Array(e),u32:new Uint32Array(e),f32:new Float32Array(e),f16:new Uint16Array(e)},o=this.getFlatUniformValues(t);for(const[s,r]of Object.entries(o))this._writeLeafValue(i,s,r);return new Uint8Array(e,0,this.layout.byteLength)}_flattenCompositeValue(t,e,i,o){if(o!==void 0){if(typeof i=="string"||this.layout.fields[e]){t[e]=o;return}if(Array.isArray(i)){const s=i[0],r=i[1];if(Array.isArray(s))throw new Error(`Nested arrays are not supported for ${e}`);if(typeof s=="string"&&Zt(o)){this._flattenPackedArray(t,e,s,r,o);return}if(!Array.isArray(o)){P.warn(`Unsupported uniform array value for ${e}:`,o)();return}for(let a=0;a<Math.min(o.length,r);a++){const l=o[a];l!==void 0&&this._flattenCompositeValue(t,`${e}[${a}]`,s,l)}return}if(An(i)&&Fs(o)){for(const[s,r]of Object.entries(o)){if(r===void 0)continue;const a=`${e}.${s}`;this._flattenCompositeValue(t,a,i[s],r)}return}P.warn(`Unsupported uniform value for ${e}:`,o)()}}_flattenPackedArray(t,e,i,o,s){const r=s,l=re(i,this.layout.layout).components;for(let c=0;c<o;c++){const u=c*l;if(u>=r.length)break;l===1?t[`${e}[${c}]`]=Number(r[u]):t[`${e}[${c}]`]=ks(s,u,u+l)}}_writeLeafValue(t,e,i){const o=this.layout.fields[e];if(!o){P.warn(`Uniform ${e} not found in layout`)();return}const{type:s,components:r,columns:a,rows:l,offset:c,columnStride:u}=o,f=t[s];if(r===1){f[c]=Number(i);return}const d=i;if(a===1){for(let p=0;p<r;p++)f[c+p]=Number(d[p]??0);return}let h=0;for(let p=0;p<a;p++){const g=c+p*u;for(let m=0;m<l;m++)f[g+m]=Number(d[h++]??0)}}}function Fs(n){return!!n&&typeof n=="object"&&!Array.isArray(n)&&!ArrayBuffer.isView(n)}function ks(n,t,e){return Array.prototype.slice.call(n,t,e)}const Bs=128;function Ns(n,t,e=16){if(n===t)return!0;const i=n,o=t;if(!Zt(i)||!Zt(o)||i.length!==o.length)return!1;const s=Math.min(e,Bs);if(i.length>s)return!1;for(let r=0;r<i.length;++r)if(o[r]!==i[r])return!1;return!0}function Us(n){return Zt(n)?n.slice():n}class Ds{constructor(t){y(this,"name");y(this,"uniforms",{});y(this,"modifiedUniforms",{});y(this,"modified",!0);y(this,"bindingLayout",{});y(this,"needsRedraw","initialized");var e;if(this.name=(t==null?void 0:t.name)||"unnamed",t!=null&&t.name&&(t!=null&&t.shaderLayout)){const i=(e=t==null?void 0:t.shaderLayout.bindings)==null?void 0:e.find(s=>s.type==="uniform"&&s.name===(t==null?void 0:t.name));if(!i)throw new Error(t==null?void 0:t.name);const o=i;for(const s of o.uniforms||[])this.bindingLayout[s.name]=s}}setUniforms(t){for(const[e,i]of Object.entries(t))this._setUniform(e,i),this.needsRedraw||this.setNeedsRedraw(`${this.name}.${e}=${i}`)}setNeedsRedraw(t){this.needsRedraw=this.needsRedraw||t}getAllUniforms(){return this.modifiedUniforms={},this.needsRedraw=!1,this.uniforms||{}}_setUniform(t,e){Ns(this.uniforms[t],e)||(this.uniforms[t]=Us(e),this.modifiedUniforms[t]=!0,this.modified=!0)}}const js=1024;class Gs{constructor(t,e){y(this,"device");y(this,"uniformBlocks",new Map);y(this,"shaderBlockLayouts",new Map);y(this,"shaderBlockWriters",new Map);y(this,"uniformBuffers",new Map);this.device=t;for(const[i,o]of Object.entries(e)){const s=i,r=Es(o.uniformTypes??{},{layout:o.layout??$s(t)}),a=new zs(r);this.shaderBlockLayouts.set(s,r),this.shaderBlockWriters.set(s,a);const l=new Ds({name:i});l.setUniforms(a.getFlatUniformValues(o.defaultUniforms||{})),this.uniformBlocks.set(s,l)}}destroy(){for(const t of this.uniformBuffers.values())t.destroy()}setUniforms(t){var e;for(const[i,o]of Object.entries(t)){const s=i,r=this.shaderBlockWriters.get(s),a=r==null?void 0:r.getFlatUniformValues(o||{});(e=this.uniformBlocks.get(s))==null||e.setUniforms(a||{})}this.updateUniformBuffers()}getUniformBufferByteLength(t){var i;const e=((i=this.shaderBlockLayouts.get(t))==null?void 0:i.byteLength)||0;return Math.max(e,js)}getUniformBufferData(t){var o;const e=((o=this.uniformBlocks.get(t))==null?void 0:o.getAllUniforms())||{},i=this.shaderBlockWriters.get(t);return(i==null?void 0:i.getData(e))||new Uint8Array(0)}createUniformBuffer(t,e){e&&this.setUniforms(e);const i=this.getUniformBufferByteLength(t),o=this.device.createBuffer({usage:R.UNIFORM|R.COPY_DST,byteLength:i}),s=this.getUniformBufferData(t);return o.write(s),o}getManagedUniformBuffer(t){if(!this.uniformBuffers.get(t)){const e=this.getUniformBufferByteLength(t),i=this.device.createBuffer({usage:R.UNIFORM|R.COPY_DST,byteLength:e});this.uniformBuffers.set(t,i)}return this.uniformBuffers.get(t)}updateUniformBuffers(){let t=!1;for(const e of this.uniformBlocks.keys()){const i=this.updateUniformBuffer(e);t||(t=i)}return t&&P.log(3,`UniformStore.updateUniformBuffers(): ${t}`)(),t}updateUniformBuffer(t){var s;const e=this.uniformBlocks.get(t);let i=this.uniformBuffers.get(t),o=!1;if(i&&(e!=null&&e.needsRedraw)){o||(o=e.needsRedraw);const r=this.getUniformBufferData(t);i=this.uniformBuffers.get(t),i==null||i.write(r);const a=(s=this.uniformBlocks.get(t))==null?void 0:s.getAllUniforms();P.log(4,`Writing to uniform buffer ${String(t)}`,r,a)()}return o}}function $s(n){return n.type==="webgpu"?"wgsl-uniform":"std140"}const mi=`precision highp int;

// #if (defined(SHADER_TYPE_FRAGMENT) && defined(LIGHTING_FRAGMENT)) || (defined(SHADER_TYPE_VERTEX) && defined(LIGHTING_VERTEX))
struct AmbientLight {
  vec3 color;
};

struct PointLight {
  vec3 color;
  vec3 position;
  vec3 attenuation; // 2nd order x:Constant-y:Linear-z:Exponential
};

struct SpotLight {
  vec3 color;
  vec3 position;
  vec3 direction;
  vec3 attenuation;
  vec2 coneCos;
};

struct DirectionalLight {
  vec3 color;
  vec3 direction;
};

struct UniformLight {
  vec3 color;
  vec3 position;
  vec3 direction;
  vec3 attenuation;
  vec2 coneCos;
};

layout(std140) uniform lightingUniforms {
  int enabled;
  int directionalLightCount;
  int pointLightCount;
  int spotLightCount;
  vec3 ambientColor;
  UniformLight lights[5];
} lighting;

PointLight lighting_getPointLight(int index) {
  UniformLight light = lighting.lights[index];
  return PointLight(light.color, light.position, light.attenuation);
}

SpotLight lighting_getSpotLight(int index) {
  UniformLight light = lighting.lights[lighting.pointLightCount + index];
  return SpotLight(light.color, light.position, light.direction, light.attenuation, light.coneCos);
}

DirectionalLight lighting_getDirectionalLight(int index) {
  UniformLight light =
    lighting.lights[lighting.pointLightCount + lighting.spotLightCount + index];
  return DirectionalLight(light.color, light.direction);
}

float getPointLightAttenuation(PointLight pointLight, float distance) {
  return pointLight.attenuation.x
       + pointLight.attenuation.y * distance
       + pointLight.attenuation.z * distance * distance;
}

float getSpotLightAttenuation(SpotLight spotLight, vec3 positionWorldspace) {
  vec3 light_direction = normalize(positionWorldspace - spotLight.position);
  float coneFactor = smoothstep(
    spotLight.coneCos.y,
    spotLight.coneCos.x,
    dot(normalize(spotLight.direction), light_direction)
  );
  float distanceAttenuation = getPointLightAttenuation(
    PointLight(spotLight.color, spotLight.position, spotLight.attenuation),
    distance(spotLight.position, positionWorldspace)
  );
  return distanceAttenuation / max(coneFactor, 0.0001);
}

// #endif
`,Vs=`// #if (defined(SHADER_TYPE_FRAGMENT) && defined(LIGHTING_FRAGMENT)) || (defined(SHADER_TYPE_VERTEX) && defined(LIGHTING_VERTEX))
const MAX_LIGHTS: i32 = 5;

struct AmbientLight {
  color: vec3<f32>,
};

struct PointLight {
  color: vec3<f32>,
  position: vec3<f32>,
  attenuation: vec3<f32>, // 2nd order x:Constant-y:Linear-z:Exponential
};

struct SpotLight {
  color: vec3<f32>,
  position: vec3<f32>,
  direction: vec3<f32>,
  attenuation: vec3<f32>,
  coneCos: vec2<f32>,
};

struct DirectionalLight {
  color: vec3<f32>,
  direction: vec3<f32>,
};

struct UniformLight {
  color: vec3<f32>,
  position: vec3<f32>,
  direction: vec3<f32>,
  attenuation: vec3<f32>,
  coneCos: vec2<f32>,
};

struct lightingUniforms {
  enabled: i32,
  directionalLightCount: i32,
  pointLightCount: i32,
  spotLightCount: i32,
  ambientColor: vec3<f32>,
  lights: array<UniformLight, 5>,
};

@group(2) @binding(auto) var<uniform> lighting : lightingUniforms;

fn lighting_getPointLight(index: i32) -> PointLight {
  let light = lighting.lights[index];
  return PointLight(light.color, light.position, light.attenuation);
}

fn lighting_getSpotLight(index: i32) -> SpotLight {
  let light = lighting.lights[lighting.pointLightCount + index];
  return SpotLight(light.color, light.position, light.direction, light.attenuation, light.coneCos);
}

fn lighting_getDirectionalLight(index: i32) -> DirectionalLight {
  let light = lighting.lights[lighting.pointLightCount + lighting.spotLightCount + index];
  return DirectionalLight(light.color, light.direction);
}

fn getPointLightAttenuation(pointLight: PointLight, distance: f32) -> f32 {
  return pointLight.attenuation.x
       + pointLight.attenuation.y * distance
       + pointLight.attenuation.z * distance * distance;
}

fn getSpotLightAttenuation(spotLight: SpotLight, positionWorldspace: vec3<f32>) -> f32 {
  let lightDirection = normalize(positionWorldspace - spotLight.position);
  let coneFactor = smoothstep(
    spotLight.coneCos.y,
    spotLight.coneCos.x,
    dot(normalize(spotLight.direction), lightDirection)
  );
  let distanceAttenuation = getPointLightAttenuation(
    PointLight(spotLight.color, spotLight.position, spotLight.attenuation),
    distance(spotLight.position, positionWorldspace)
  );
  return distanceAttenuation / max(coneFactor, 0.0001);
}
`,tt=5,Ws={color:"vec3<f32>",position:"vec3<f32>",direction:"vec3<f32>",attenuation:"vec3<f32>",coneCos:"vec2<f32>"},In={props:{},uniforms:{},name:"lighting",defines:{},uniformTypes:{enabled:"i32",directionalLightCount:"i32",pointLightCount:"i32",spotLightCount:"i32",ambientColor:"vec3<f32>",lights:[Ws,tt]},defaultUniforms:Dt(),bindingLayout:[{name:"lighting",group:2}],firstBindingSlot:0,source:Vs,vs:mi,fs:mi,getUniforms:Hs};function Hs(n,t={}){if(n=n&&{...n},!n)return Dt();n.lights&&(n={...n,...Ys(n.lights),lights:void 0});const{useByteColors:e,ambientLight:i,pointLights:o,spotLights:s,directionalLights:r}=n||{};if(!(i||o&&o.length>0||s&&s.length>0||r&&r.length>0))return{...Dt(),enabled:0};const l={...Dt(),...Ks({useByteColors:e,ambientLight:i,pointLights:o,spotLights:s,directionalLights:r})};return n.enabled!==void 0&&(l.enabled=n.enabled?1:0),l}function Ks({useByteColors:n,ambientLight:t,pointLights:e=[],spotLights:i=[],directionalLights:o=[]}){const s=On();let r=0,a=0,l=0,c=0;for(const u of e){if(r>=tt)break;s[r]={...s[r],color:It(u,n),position:u.position,attenuation:u.attenuation||[1,0,0]},r++,a++}for(const u of i){if(r>=tt)break;s[r]={...s[r],color:It(u,n),position:u.position,direction:u.direction,attenuation:u.attenuation||[1,0,0],coneCos:qs(u)},r++,l++}for(const u of o){if(r>=tt)break;s[r]={...s[r],color:It(u,n),direction:u.direction},r++,c++}return e.length+i.length+o.length>tt&&P.warn(`MAX_LIGHTS exceeded, truncating to ${tt}`)(),{ambientColor:It(t,n),directionalLightCount:c,pointLightCount:a,spotLightCount:l,lights:s}}function Ys(n){var e,i,o;const t={pointLights:[],spotLights:[],directionalLights:[]};for(const s of n||[])switch(s.type){case"ambient":t.ambientLight=s;break;case"directional":(e=t.directionalLights)==null||e.push(s);break;case"point":(i=t.pointLights)==null||i.push(s);break;case"spot":(o=t.spotLights)==null||o.push(s);break}return t}function It(n={},t){const{color:e=[0,0,0],intensity:i=1}=n;return Ln(e,Cn(t,!0)).map(s=>s*i)}function Dt(){return{enabled:1,directionalLightCount:0,pointLightCount:0,spotLightCount:0,ambientColor:[.1,.1,.1],lights:On()}}function On(){return Array.from({length:tt},()=>Zs())}function Zs(){return{color:[1,1,1],position:[1,1,2],direction:[1,1,1],attenuation:[1,0,0],coneCos:[1,0]}}function qs(n){const t=n.innerConeAngle??0,e=n.outerConeAngle??Math.PI/4;return[Math.cos(t),Math.cos(e)]}const Mn=`layout(std140) uniform phongMaterialUniforms {
  uniform bool unlit;
  uniform float ambient;
  uniform float diffuse;
  uniform float shininess;
  uniform vec3  specularColor;
} material;
`,Rn=`layout(std140) uniform phongMaterialUniforms {
  uniform bool unlit;
  uniform float ambient;
  uniform float diffuse;
  uniform float shininess;
  uniform vec3  specularColor;
} material;

vec3 lighting_getLightColor(vec3 surfaceColor, vec3 light_direction, vec3 view_direction, vec3 normal_worldspace, vec3 color) {
  vec3 halfway_direction = normalize(light_direction + view_direction);
  float lambertian = dot(light_direction, normal_worldspace);
  float specular = 0.0;
  if (lambertian > 0.0) {
    float specular_angle = max(dot(normal_worldspace, halfway_direction), 0.0);
    specular = pow(specular_angle, material.shininess);
  }
  lambertian = max(lambertian, 0.0);
  return (lambertian * material.diffuse * surfaceColor + specular * floatColors_normalize(material.specularColor)) * color;
}

vec3 lighting_getLightColor(vec3 surfaceColor, vec3 cameraPosition, vec3 position_worldspace, vec3 normal_worldspace) {
  vec3 lightColor = surfaceColor;

  if (material.unlit) {
    return surfaceColor;
  }

  if (lighting.enabled == 0) {
    return lightColor;
  }

  vec3 view_direction = normalize(cameraPosition - position_worldspace);
  lightColor = material.ambient * surfaceColor * lighting.ambientColor;

  for (int i = 0; i < lighting.pointLightCount; i++) {
    PointLight pointLight = lighting_getPointLight(i);
    vec3 light_position_worldspace = pointLight.position;
    vec3 light_direction = normalize(light_position_worldspace - position_worldspace);
    float light_attenuation = getPointLightAttenuation(pointLight, distance(light_position_worldspace, position_worldspace));
    lightColor += lighting_getLightColor(surfaceColor, light_direction, view_direction, normal_worldspace, pointLight.color / light_attenuation);
  }

  for (int i = 0; i < lighting.spotLightCount; i++) {
    SpotLight spotLight = lighting_getSpotLight(i);
    vec3 light_position_worldspace = spotLight.position;
    vec3 light_direction = normalize(light_position_worldspace - position_worldspace);
    float light_attenuation = getSpotLightAttenuation(spotLight, position_worldspace);
    lightColor += lighting_getLightColor(surfaceColor, light_direction, view_direction, normal_worldspace, spotLight.color / light_attenuation);
  }

  for (int i = 0; i < lighting.directionalLightCount; i++) {
    DirectionalLight directionalLight = lighting_getDirectionalLight(i);
    lightColor += lighting_getLightColor(surfaceColor, -directionalLight.direction, view_direction, normal_worldspace, directionalLight.color);
  }
  
  return lightColor;
}
`,zn=`struct phongMaterialUniforms {
  unlit: u32,
  ambient: f32,
  diffuse: f32,
  shininess: f32,
  specularColor: vec3<f32>,
};

@group(3) @binding(auto) var<uniform> phongMaterial : phongMaterialUniforms;

fn lighting_getLightColor(surfaceColor: vec3<f32>, light_direction: vec3<f32>, view_direction: vec3<f32>, normal_worldspace: vec3<f32>, color: vec3<f32>) -> vec3<f32> {
  let halfway_direction: vec3<f32> = normalize(light_direction + view_direction);
  var lambertian: f32 = dot(light_direction, normal_worldspace);
  var specular: f32 = 0.0;
  if (lambertian > 0.0) {
    let specular_angle = max(dot(normal_worldspace, halfway_direction), 0.0);
    specular = pow(specular_angle, phongMaterial.shininess);
  }
  lambertian = max(lambertian, 0.0);
  return (
    lambertian * phongMaterial.diffuse * surfaceColor +
    specular * floatColors_normalize(phongMaterial.specularColor)
  ) * color;
}

fn lighting_getLightColor2(surfaceColor: vec3<f32>, cameraPosition: vec3<f32>, position_worldspace: vec3<f32>, normal_worldspace: vec3<f32>) -> vec3<f32> {
  var lightColor: vec3<f32> = surfaceColor;

  if (phongMaterial.unlit != 0u) {
    return surfaceColor;
  }

  if (lighting.enabled == 0) {
    return lightColor;
  }

  let view_direction: vec3<f32> = normalize(cameraPosition - position_worldspace);
  lightColor = phongMaterial.ambient * surfaceColor * lighting.ambientColor;

  for (var i: i32 = 0; i < lighting.pointLightCount; i++) {
    let pointLight: PointLight = lighting_getPointLight(i);
    let light_position_worldspace: vec3<f32> = pointLight.position;
    let light_direction: vec3<f32> = normalize(light_position_worldspace - position_worldspace);
    let light_attenuation = getPointLightAttenuation(
      pointLight,
      distance(light_position_worldspace, position_worldspace)
    );
    lightColor += lighting_getLightColor(
      surfaceColor,
      light_direction,
      view_direction,
      normal_worldspace,
      pointLight.color / light_attenuation
    );
  }

  for (var i: i32 = 0; i < lighting.spotLightCount; i++) {
    let spotLight: SpotLight = lighting_getSpotLight(i);
    let light_position_worldspace: vec3<f32> = spotLight.position;
    let light_direction: vec3<f32> = normalize(light_position_worldspace - position_worldspace);
    let light_attenuation = getSpotLightAttenuation(spotLight, position_worldspace);
    lightColor += lighting_getLightColor(
      surfaceColor,
      light_direction,
      view_direction,
      normal_worldspace,
      spotLight.color / light_attenuation
    );
  }

  for (var i: i32 = 0; i < lighting.directionalLightCount; i++) {
    let directionalLight: DirectionalLight = lighting_getDirectionalLight(i);
    lightColor += lighting_getLightColor(surfaceColor, -directionalLight.direction, view_direction, normal_worldspace, directionalLight.color);
  }  
  
  return lightColor;
}

fn lighting_getSpecularLightColor(cameraPosition: vec3<f32>, position_worldspace: vec3<f32>, normal_worldspace: vec3<f32>) -> vec3<f32>{
  var lightColor = vec3<f32>(0, 0, 0);
  let surfaceColor = vec3<f32>(0, 0, 0);

  if (lighting.enabled != 0) {
    let view_direction = normalize(cameraPosition - position_worldspace);

    for (var i: i32 = 0; i < lighting.pointLightCount; i++) {
      let pointLight: PointLight = lighting_getPointLight(i);
      let light_position_worldspace: vec3<f32> = pointLight.position;
      let light_direction: vec3<f32> = normalize(light_position_worldspace - position_worldspace);
      let light_attenuation = getPointLightAttenuation(
        pointLight,
        distance(light_position_worldspace, position_worldspace)
      );
      lightColor += lighting_getLightColor(
        surfaceColor,
        light_direction,
        view_direction,
        normal_worldspace,
        pointLight.color / light_attenuation
      );
    }

    for (var i: i32 = 0; i < lighting.spotLightCount; i++) {
      let spotLight: SpotLight = lighting_getSpotLight(i);
      let light_position_worldspace: vec3<f32> = spotLight.position;
      let light_direction: vec3<f32> = normalize(light_position_worldspace - position_worldspace);
      let light_attenuation = getSpotLightAttenuation(spotLight, position_worldspace);
      lightColor += lighting_getLightColor(
        surfaceColor,
        light_direction,
        view_direction,
        normal_worldspace,
        spotLight.color / light_attenuation
      );
    }

    for (var i: i32 = 0; i < lighting.directionalLightCount; i++) {
        let directionalLight: DirectionalLight = lighting_getDirectionalLight(i);
        lightColor += lighting_getLightColor(surfaceColor, -directionalLight.direction, view_direction, normal_worldspace, directionalLight.color);
    }
  }
  return lightColor;
}
`,Xs=[38.25,38.25,38.25],ae={props:{},name:"gouraudMaterial",bindingLayout:[{name:"gouraudMaterial",group:3}],vs:Rn.replace("phongMaterial","gouraudMaterial"),fs:Mn.replace("phongMaterial","gouraudMaterial"),source:zn.replaceAll("phongMaterial","gouraudMaterial"),defines:{LIGHTING_VERTEX:!0},dependencies:[In,wn],uniformTypes:{unlit:"i32",ambient:"f32",diffuse:"f32",shininess:"f32",specularColor:"vec3<f32>"},defaultUniforms:{unlit:!1,ambient:.35,diffuse:.6,shininess:32,specularColor:Xs},getUniforms(n){return{...ae.defaultUniforms,...n}}},Js=[38.25,38.25,38.25],Fn={name:"phongMaterial",firstBindingSlot:0,bindingLayout:[{name:"phongMaterial",group:3}],dependencies:[In,wn],source:zn,vs:Mn,fs:Rn,defines:{LIGHTING_FRAGMENT:!0},uniformTypes:{unlit:"i32",ambient:"f32",diffuse:"f32",shininess:"f32",specularColor:"vec3<f32>"},defaultUniforms:{unlit:!1,ambient:.35,diffuse:.6,shininess:32,specularColor:Js},getUniforms(n){return{...Fn.defaultUniforms,...n}}},Qs=`

@must_use
fn deckgl_premultiplied_alpha(fragColor: vec4<f32>) -> vec4<f32> {
    return vec4(fragColor.rgb * fragColor.a, fragColor.a); 
};
`,le={name:"color",dependencies:[],source:Qs,getUniforms:n=>({})},tr=`// Define a structure to hold both the clip-space position and the common position.
struct ProjectResult {
  clipPosition: vec4<f32>,
  commonPosition: vec4<f32>,
};

// This function mimics the GLSL version with the 'out' parameter by returning both values.
fn project_position_to_clipspace_and_commonspace(
    position: vec3<f32>,
    position64Low: vec3<f32>,
    offset: vec3<f32>
) -> ProjectResult {
  // Compute the projected position.
  let projectedPosition: vec3<f32> = project_position_vec3_f64(position, position64Low);

  // Start with the provided offset.
  var finalOffset: vec3<f32> = offset;

  // Get whether a rotation is needed and the rotation matrix.
  let rotationResult = project_needs_rotation(projectedPosition);

  // If rotation is needed, update the offset.
  if (rotationResult.needsRotation) {
    finalOffset = rotationResult.transform * offset;
  }

  // Compute the common position.
  let commonPosition: vec4<f32> = vec4<f32>(projectedPosition + finalOffset, 1.0);

  // Convert to clip-space.
  let clipPosition: vec4<f32> = project_common_position_to_clipspace(commonPosition);

  return ProjectResult(clipPosition, commonPosition);
}

// A convenience overload that returns only the clip-space position.
fn project_position_to_clipspace(
    position: vec3<f32>,
    position64Low: vec3<f32>,
    offset: vec3<f32>
) -> vec4<f32> {
  return project_position_to_clipspace_and_commonspace(position, position64Low, offset).clipPosition;
}
`,er=`vec4 project_position_to_clipspace(
  vec3 position, vec3 position64Low, vec3 offset, out vec4 commonPosition
) {
  vec3 projectedPosition = project_position(position, position64Low);
  mat3 rotation;
  if (project_needs_rotation(projectedPosition, rotation)) {
    // offset is specified as ENU
    // when in globe projection, rotate offset so that the ground alighs with the surface of the globe
    offset = rotation * offset;
  }
  commonPosition = vec4(projectedPosition + offset, 1.0);
  return project_common_position_to_clipspace(commonPosition);
}

vec4 project_position_to_clipspace(
  vec3 position, vec3 position64Low, vec3 offset
) {
  vec4 commonPosition;
  return project_position_to_clipspace(position, position64Low, offset, commonPosition);
}
`,V={name:"project32",dependencies:[Yo],source:tr,vs:er},ir=`struct pickingUniforms {
  isActive: f32,
  isAttribute: f32,
  isHighlightActive: f32,
  useByteColors: f32,
  highlightedObjectColor: vec3<f32>,
  highlightColor: vec4<f32>,
};

@group(0) @binding(auto) var<uniform> picking: pickingUniforms;

fn picking_normalizeColor(color: vec3<f32>) -> vec3<f32> {
  return select(color, color / 255.0, picking.useByteColors > 0.5);
}

fn picking_normalizeColor4(color: vec4<f32>) -> vec4<f32> {
  return select(color, color / 255.0, picking.useByteColors > 0.5);
}

fn picking_isColorZero(color: vec3<f32>) -> bool {
  return dot(color, vec3<f32>(1.0)) < 0.00001;
}

fn picking_isColorValid(color: vec3<f32>) -> bool {
  return dot(color, vec3<f32>(1.0)) > 0.00001;
}
`,W={...pi,source:ir,defaultUniforms:{...pi.defaultUniforms,useByteColors:!0},inject:{"vs:DECKGL_FILTER_GL_POSITION":`
    // for picking depth values
    picking_setPickingAttribute(position.z / position.w);
  `,"vs:DECKGL_FILTER_COLOR":`
  picking_setPickingColor(geometry.pickingColor);
  `,"fs:DECKGL_FILTER_COLOR":{order:99,injection:`
  // use highlight color if this fragment belongs to the selected object.
  color = picking_filterHighlightColor(color);

  // use picking color if rendering to picking FBO.
  color = picking_filterPickingColor(color);
    `}}},yi=[0,0,0];function _e(n,t,e=!1){const i=t.projectPosition(n);if(e&&t instanceof Qo){const[o,s,r=0]=n,a=t.getDistanceScales([o,s]);i[2]=r*a.unitsPerMeter[2]}return i}function nr(n){const{viewport:t,modelMatrix:e,coordinateOrigin:i}=n;let{coordinateSystem:o,fromCoordinateSystem:s,fromCoordinateOrigin:r}=n;return o==="default"&&(o=t.isGeospatial?"lnglat":"cartesian"),s===void 0?s=o:s==="default"&&(s=t.isGeospatial?"lnglat":"cartesian"),r===void 0&&(r=i),{viewport:t,coordinateSystem:o,coordinateOrigin:i,modelMatrix:e,fromCoordinateSystem:s,fromCoordinateOrigin:r}}function Je(n,{viewport:t,modelMatrix:e,coordinateSystem:i,coordinateOrigin:o,offsetMode:s}){let[r,a,l=0]=n;switch(e&&([r,a,l]=Zo([],[r,a,l,1],e)),i){case"default":return Je(n,{viewport:t,modelMatrix:e,coordinateSystem:t.isGeospatial?"lnglat":"cartesian",coordinateOrigin:o,offsetMode:s});case"lnglat":return _e([r,a,l],t,s);case"lnglat-offsets":return _e([r+o[0],a+o[1],l+(o[2]||0)],t,s);case"meter-offsets":return _e(qo(o,[r,a,l]),t,s);case"cartesian":return t.isGeospatial?[r+o[0],a+o[1],l+o[2]]:t.projectPosition([r,a,l]);default:throw new Error(`Invalid coordinateSystem: ${i}`)}}function or(n,t){const{viewport:e,coordinateSystem:i,coordinateOrigin:o,modelMatrix:s,fromCoordinateSystem:r,fromCoordinateOrigin:a}=nr(t),{autoOffset:l=!0}=t,{geospatialOrigin:c=yi,shaderCoordinateOrigin:u=yi,offsetMode:f=!1}=l?Xo(e,i,o):{},d=Je(n,{viewport:e,modelMatrix:s,coordinateSystem:r,coordinateOrigin:a,offsetMode:f});if(f){const h=e.projectPosition(c||u);Jo(d,d,h)}return d}const xe={};function St(n="id"){xe[n]=xe[n]||1;const t=xe[n]++;return`${n}-${t}`}class vi{constructor(t){y(this,"id");y(this,"userData",{});y(this,"topology");y(this,"bufferLayout",[]);y(this,"vertexCount");y(this,"indices");y(this,"attributes");if(this.id=t.id||St("geometry"),this.topology=t.topology,this.indices=t.indices||null,this.attributes=t.attributes,this.vertexCount=t.vertexCount,this.bufferLayout=t.bufferLayout||[],this.indices&&!(this.indices.usage&R.INDEX))throw new Error("Index buffer must have INDEX usage")}destroy(){var t;(t=this.indices)==null||t.destroy();for(const e of Object.values(this.attributes))e.destroy()}getVertexCount(){return this.vertexCount}getAttributes(){return this.attributes}getIndexes(){return this.indices||null}_calculateVertexCount(t){return t.byteLength/12}}function sr(n,t){if(t instanceof vi)return t;const e=rr(n,t),{attributes:i,bufferLayout:o}=ar(n,t);return new vi({topology:t.topology||"triangle-list",bufferLayout:o,vertexCount:t.vertexCount,indices:e,attributes:i})}function rr(n,t){if(!t.indices)return;const e=t.indices.value;return n.createBuffer({usage:R.INDEX,data:e})}function ar(n,t){const e=[],i={};for(const[s,r]of Object.entries(t.attributes)){let a=s;switch(s){case"POSITION":a="positions";break;case"NORMAL":a="normals";break;case"TEXCOORD_0":a="texCoords";break;case"TEXCOORD_1":a="texCoords1";break;case"COLOR_0":a="colors";break}if(r){i[a]=n.createBuffer({data:r.value,id:`${s}-buffer`});const{value:l,size:c,normalized:u}=r;if(c===void 0)throw new Error(`Attribute ${s} is missing a size`);e.push({name:a,format:ts.getVertexFormatFromAttribute(l,c,u)})}}const o=t._calculateVertexCount(t.attributes,t.indices);return{attributes:i,bufferLayout:e,vertexCount:o}}function lr(n,t){var o;const e={},i="Values";if(n.attributes.length===0&&!((o=n.varyings)!=null&&o.length))return{"No attributes or varyings":{[i]:"N/A"}};for(const s of n.attributes)if(s){const r=`${s.location} ${s.name}: ${s.type}`;e[`in ${r}`]={[i]:s.stepMode||"vertex"}}for(const s of n.varyings||[]){const r=`${s.location} ${s.name}`;e[`out ${r}`]={[i]:JSON.stringify(s)}}return e}const Ot="__debugFramebufferState",be=8;function cr(n,t,e){if(n.device.type!=="webgl")return;const i=dr(n.device);if(!i.flushing){if(pr(n)){ur(n,e,i);return}t&&hr(t)&&t.handle!==null&&(i.queuedFramebuffers.includes(t)||i.queuedFramebuffers.push(t))}}function ur(n,t,e){if(e.queuedFramebuffers.length===0)return;const i=n.device,{gl:o}=i,s=o.getParameter(36010),r=o.getParameter(36006),[a,l]=n.device.getDefaultCanvasContext().getDrawingBufferSize();let c=_i(t.top,be);const u=_i(t.left,be);e.flushing=!0;try{for(const f of e.queuedFramebuffers){const[d,h,p,g,m]=fr({framebuffer:f,targetWidth:a,targetHeight:l,topPx:c,leftPx:u,minimap:t.minimap});o.bindFramebuffer(36008,f.handle),o.bindFramebuffer(36009,null),o.blitFramebuffer(0,0,f.width,f.height,d,h,p,g,16384,9728),c+=m+be}}finally{o.bindFramebuffer(36008,s),o.bindFramebuffer(36009,r),e.flushing=!1}}function fr(n){const{framebuffer:t,targetWidth:e,targetHeight:i,topPx:o,leftPx:s}=n,r=Math.max(Math.floor(e/4),1),a=Math.max(Math.floor(i/4),1),l=Math.min(r/t.width,a/t.height),c=Math.max(Math.floor(t.width*l),1),u=Math.max(Math.floor(t.height*l),1),f=s,d=Math.max(i-o-u,0),h=f+c,p=d+u;return[f,d,h,p,u]}function dr(n){var t;return(t=n.userData)[Ot]||(t[Ot]={flushing:!1,queuedFramebuffers:[]}),n.userData[Ot]}function hr(n){return"colorAttachments"in n}function pr(n){const t=n.props.framebuffer;return!t||t.handle===null}function _i(n,t){if(!n)return t;const e=Number.parseInt(n,10);return Number.isFinite(e)?e:t}function Fe(n,t,e){if(n===t)return!0;if(!e||!n||!t)return!1;if(Array.isArray(n)){if(!Array.isArray(t)||n.length!==t.length)return!1;for(let i=0;i<n.length;i++)if(!Fe(n[i],t[i],e-1))return!1;return!0}if(Array.isArray(t))return!1;if(typeof n=="object"&&typeof t=="object"){const i=Object.keys(n),o=Object.keys(t);if(i.length!==o.length)return!1;for(const s of i)if(!t.hasOwnProperty(s)||!Fe(n[s],t[s],e-1))return!1;return!0}return!1}class Pe{constructor(t){y(this,"bufferLayouts");this.bufferLayouts=t}getBufferLayout(t){return this.bufferLayouts.find(e=>e.name===t)||null}getAttributeNamesForBuffer(t){var e;return t.attributes?(e=t.attributes)==null?void 0:e.map(i=>i.attribute):[t.name]}mergeBufferLayouts(t,e){const i=[...t];for(const o of e){const s=i.findIndex(r=>r.name===o.name);s<0?i.push(o):i[s]=o}return i}getBufferIndex(t){const e=this.bufferLayouts.findIndex(i=>i.name===t);return e===-1&&P.warn(`BufferLayout: Missing buffer for "${t}".`)(),e}}function xi(n,t){let e=1/0;for(const i of n){const o=t[i];o!==void 0&&(e=Math.min(e,o))}return e}function gr(n,t){const e=Object.fromEntries(n.attributes.map(o=>[o.name,o.location])),i=t.slice();return i.sort((o,s)=>{const r=o.attributes?o.attributes.map(u=>u.attribute):[o.name],a=s.attributes?s.attributes.map(u=>u.attribute):[s.name],l=xi(r,e),c=xi(a,e);return l-c}),i}function bi(n,t){if(!n||!t.some(i=>{var o;return(o=i.bindingLayout)==null?void 0:o.length}))return n;const e={...n,bindings:n.bindings.map(i=>({...i}))};"attributes"in(n||{})&&(e.attributes=(n==null?void 0:n.attributes)||[]);for(const i of t)for(const o of i.bindingLayout||[])for(const s of yr(o.name)){const r=e.bindings.find(a=>a.name===s);(r==null?void 0:r.group)===0&&(r.group=o.group)}return e}function mr(n){return!!(n.uniformTypes&&!vr(n.uniformTypes))}function yr(n){const t=new Set([n,`${n}Uniforms`]);return n.endsWith("Uniforms")||t.add(`${n}Sampler`),[...t]}function vr(n){for(const t in n)return!1;return!0}function _r(n){return ds(n)||typeof n=="number"||typeof n=="boolean"}function xr(n,t={}){const e={bindings:{},uniforms:{}};return Object.keys(n).forEach(i=>{const o=n[i];Object.prototype.hasOwnProperty.call(t,i)||_r(o)?e.uniforms[i]=o:e.bindings[i]=o}),e}class br{constructor(t,e){y(this,"options",{disableWarnings:!1});y(this,"modules");y(this,"moduleUniforms");y(this,"moduleBindings");Object.assign(this.options,e);const i=es(Object.values(t).filter(Pr));for(const o of i)t[o.name]=o;P.log(1,"Creating ShaderInputs with modules",Object.keys(t))(),this.modules=t,this.moduleUniforms={},this.moduleBindings={};for(const[o,s]of Object.entries(t))s&&(this._addModule(s),s.name&&o!==s.name&&!this.options.disableWarnings&&P.warn(`Module name: ${o} vs ${s.name}`)())}destroy(){}setProps(t){var e;for(const i of Object.keys(t)){const o=i,s=t[o]||{},r=this.modules[o];if(!r)this.options.disableWarnings||P.warn(`Module ${i} not found`)();else{const a=this.moduleUniforms[o],l=this.moduleBindings[o],c=((e=r.getUniforms)==null?void 0:e.call(r,s,a))||s,{uniforms:u,bindings:f}=xr(c,r.uniformTypes);this.moduleUniforms[o]=Pi(a,u,r.uniformTypes),this.moduleBindings[o]={...l,...f}}}}getModules(){return Object.values(this.modules)}getUniformValues(){return this.moduleUniforms}getBindingValues(){const t={};for(const e of Object.values(this.moduleBindings))Object.assign(t,e);return t}getDebugTable(){var e;const t={};for(const[i,o]of Object.entries(this.moduleUniforms))for(const[s,r]of Object.entries(o))t[`${i}.${s}`]={type:(e=this.modules[i].uniformTypes)==null?void 0:e[s],value:String(r)};return t}_addModule(t){const e=t.name;this.moduleUniforms[e]=Pi({},t.defaultUniforms||{},t.uniformTypes),this.moduleBindings[e]={}}}function Pi(n={},t={},e={}){const i={...n};for(const[o,s]of Object.entries(t))s!==void 0&&(i[o]=ke(n[o],s,e[o]));return i}function ke(n,t,e){if(!e||typeof e=="string")return yt(t);if(Array.isArray(e)){if(Be(t)||!Array.isArray(t))return yt(t);const r=Array.isArray(n)&&!Be(n)?[...n]:[],a=r.slice();for(let l=0;l<t.length;l++){const c=t[l];c!==void 0&&(a[l]=ke(r[l],c,e[0]))}return a}if(!Ne(t))return yt(t);const i=e,o=Ne(n)?n:{},s={...o};for(const[r,a]of Object.entries(t))a!==void 0&&(s[r]=ke(o[r],a,i[r]));return s}function yt(n){return ArrayBuffer.isView(n)?Array.prototype.slice.call(n):Array.isArray(n)?Be(n)?n.slice():n.map(e=>e===void 0?void 0:yt(e)):Ne(n)?Object.fromEntries(Object.entries(n).map(([t,e])=>[t,e===void 0?void 0:yt(e)])):n}function Be(n){return ArrayBuffer.isView(n)||Array.isArray(n)&&(n.length===0||typeof n[0]=="number")}function Ne(n){return!!n&&typeof n=="object"&&!Array.isArray(n)&&!ArrayBuffer.isView(n)}function Pr(n){return!!(n!=null&&n.dependencies)}const kn={"+X":0,"-X":1,"+Y":2,"-Y":3,"+Z":4,"-Z":5};function ft(n){return n?Array.isArray(n)?n[0]??null:n:null}function Cr(n){const{dimension:t,data:e}=n;if(!e)return null;switch(t){case"1d":{const i=ft(e);if(!i)return null;const{width:o}=dt(i);return{width:o,height:1}}case"2d":{const i=ft(e);return i?dt(i):null}case"3d":case"2d-array":{if(!Array.isArray(e)||e.length===0)return null;const i=ft(e[0]);return i?dt(i):null}case"cube":{const i=Object.keys(e)[0]??null;if(!i)return null;const o=e[i],s=ft(o);return s?dt(s):null}case"cube-array":{if(!Array.isArray(e)||e.length===0)return null;const i=e[0],o=Object.keys(i)[0]??null;if(!o)return null;const s=ft(i[o]);return s?dt(s):null}default:return null}}function dt(n){if(_n(n))return is(n);if(typeof n=="object"&&"width"in n&&"height"in n)return{width:n.width,height:n.height};throw new Error("Unsupported mip-level data")}function Lr(n){return typeof n=="object"&&n!==null&&"data"in n&&"width"in n&&"height"in n}function wr(n){return ArrayBuffer.isView(n)}function Bn(n){const{textureFormat:t,format:e}=n;if(t&&e&&t!==e)throw new Error(`Conflicting texture formats "${t}" and "${e}" provided for the same mip level`);return t??e}function Nn(n){const t=kn[n];if(t===void 0)throw new Error(`Invalid cube face: ${n}`);return t}function Ar(n,t){return 6*n+Nn(t)}function Un(n){throw new Error("setTexture1DData not supported in WebGL.")}function Sr(n){return Array.isArray(n)?n:[n]}function lt(n,t,e,i){const o=Sr(t),s=n,r=[];for(let a=0;a<o.length;a++){const l=o[a];if(_n(l))r.push({type:"external-image",image:l,z:s,mipLevel:a});else if(Lr(l))r.push({type:"texture-data",data:l,textureFormat:Bn(l),z:s,mipLevel:a});else if(wr(l)&&e)r.push({type:"texture-data",data:{data:l,width:Math.max(1,e.width>>a),height:Math.max(1,e.height>>a),...i?{format:i}:{}},textureFormat:i,z:s,mipLevel:a});else throw new Error("Unsupported 2D mip-level payload")}return r}function Dn(n){const t=[];for(let e=0;e<n.length;e++)t.push(...lt(e,n[e]));return t}function jn(n){const t=[];for(let e=0;e<n.length;e++)t.push(...lt(e,n[e]));return t}function Gn(n){const t=[];for(const[e,i]of Object.entries(n)){const o=Nn(e);t.push(...lt(o,i))}return t}function $n(n){const t=[];return n.forEach((e,i)=>{for(const[o,s]of Object.entries(e)){const r=Ar(i,o);t.push(...lt(r,s))}}),t}const oe=class oe{constructor(t,e){y(this,"device");y(this,"id");y(this,"props");y(this,"_texture",null);y(this,"_sampler",null);y(this,"_view",null);y(this,"ready");y(this,"isReady",!1);y(this,"destroyed",!1);y(this,"resolveReady",()=>{});y(this,"rejectReady",()=>{});this.device=t;const i=St("dynamic-texture"),o=e;this.props={...oe.defaultProps,id:i,...e,data:null},this.id=this.props.id,this.ready=new Promise((s,r)=>{this.resolveReady=s,this.rejectReady=r}),this.initAsync(o)}get texture(){if(!this._texture)throw new Error("Texture not initialized yet");return this._texture}get sampler(){if(!this._sampler)throw new Error("Sampler not initialized yet");return this._sampler}get view(){if(!this._view)throw new Error("View not initialized yet");return this._view}get[Symbol.toStringTag](){return"DynamicTexture"}toString(){var i,o;const t=((i=this._texture)==null?void 0:i.width)??this.props.width??"?",e=((o=this._texture)==null?void 0:o.height)??this.props.height??"?";return`DynamicTexture:"${this.id}":${t}x${e}px:(${this.isReady?"ready":"loading..."})`}async initAsync(t){try{const e=await this._loadAllData(t);this._checkNotDestroyed();const i=e.data?Tr({...e,width:t.width,height:t.height,format:t.format}):[],o="format"in t&&t.format!==void 0,s="usage"in t&&t.usage!==void 0,a=(()=>{if(this.props.width&&this.props.height)return{width:this.props.width,height:this.props.height};const g=Cr(e);return g||{width:this.props.width||1,height:this.props.height||1}})();if(!a||a.width<=0||a.height<=0)throw new Error(`${this} size could not be determined or was zero`);const l=Er(this.device,i,a,{format:o?t.format:void 0}),c=l.format??this.props.format,u={...this.props,...a,format:c,mipLevels:1,data:void 0};this.device.isTextureFormatCompressed(c)&&!s&&(u.usage=k.SAMPLE|k.COPY_DST);const f=this.props.mipmaps&&!l.hasExplicitMipChain&&!this.device.isTextureFormatCompressed(c);if(this.device.type==="webgpu"&&f){const g=this.props.dimension==="3d"?k.SAMPLE|k.STORAGE|k.COPY_DST|k.COPY_SRC:k.SAMPLE|k.RENDER|k.COPY_DST|k.COPY_SRC;u.usage|=g}const d=this.device.getMipLevelCount(u.width,u.height),h=l.hasExplicitMipChain?l.mipLevels:this.props.mipLevels==="auto"?d:Math.max(1,Math.min(d,this.props.mipLevels??1)),p={...u,mipLevels:h};this._texture=this.device.createTexture(p),this._sampler=this.texture.sampler,this._view=this.texture.view,l.subresources.length&&this._setTextureSubresources(l.subresources),this.props.mipmaps&&!l.hasExplicitMipChain&&!f&&P.warn(`${this} skipping auto-generated mipmaps for compressed texture format`)(),f&&this.generateMipmaps(),this.isReady=!0,this.resolveReady(this.texture),P.info(0,`${this} created`)()}catch(e){const i=e instanceof Error?e:new Error(String(e));this.rejectReady(i)}}destroy(){this._texture&&(this._texture.destroy(),this._texture=null,this._sampler=null,this._view=null),this.destroyed=!0}generateMipmaps(){this.device.type==="webgl"?this.texture.generateMipmapsWebGL():this.device.type==="webgpu"?this.device.generateMipmapsWebGPU(this.texture):P.warn(`${this} mipmaps not supported on ${this.device.type}`)}setSampler(t={}){this._checkReady();const e=t instanceof xn?t:this.device.createSampler(t);this.texture.setSampler(e),this._sampler=e}async readBuffer(t={}){this.isReady||await this.ready;const e=t.width??this.texture.width,i=t.height??this.texture.height,o=t.depthOrArrayLayers??this.texture.depth,s=this.texture.computeMemoryLayout({width:e,height:i,depthOrArrayLayers:o}),r=this.device.createBuffer({byteLength:s.byteLength,usage:R.COPY_DST|R.MAP_READ});this.texture.readBuffer({...t,width:e,height:i,depthOrArrayLayers:o},r);const a=this.device.createFence();return await a.signaled,a.destroy(),r}async readAsync(t={}){this.isReady||await this.ready;const e=t.width??this.texture.width,i=t.height??this.texture.height,o=t.depthOrArrayLayers??this.texture.depth,s=this.texture.computeMemoryLayout({width:e,height:i,depthOrArrayLayers:o}),r=await this.readBuffer(t),a=await r.readAsync(0,s.byteLength);return r.destroy(),a.buffer}resize(t){if(this._checkReady(),t.width===this.texture.width&&t.height===this.texture.height)return!1;const e=this.texture;return this._texture=e.clone(t),this._sampler=this.texture.sampler,this._view=this.texture.view,e.destroy(),P.info(`${this} resized`),!0}getCubeFaceIndex(t){const e=kn[t];if(e===void 0)throw new Error(`Invalid cube face: ${t}`);return e}getCubeArrayFaceIndex(t,e){return 6*t+this.getCubeFaceIndex(e)}setTexture1DData(t){if(this._checkReady(),this.texture.props.dimension!=="1d")throw new Error(`${this} is not 1d`);const e=Un();this._setTextureSubresources(e)}setTexture2DData(t,e=0){if(this._checkReady(),this.texture.props.dimension!=="2d")throw new Error(`${this} is not 2d`);const i=lt(e,t);this._setTextureSubresources(i)}setTexture3DData(t){if(this.texture.props.dimension!=="3d")throw new Error(`${this} is not 3d`);const e=Dn(t);this._setTextureSubresources(e)}setTextureArrayData(t){if(this.texture.props.dimension!=="2d-array")throw new Error(`${this} is not 2d-array`);const e=jn(t);this._setTextureSubresources(e)}setTextureCubeData(t){if(this.texture.props.dimension!=="cube")throw new Error(`${this} is not cube`);const e=Gn(t);this._setTextureSubresources(e)}setTextureCubeArrayData(t){if(this.texture.props.dimension!=="cube-array")throw new Error(`${this} is not cube-array`);const e=$n(t);this._setTextureSubresources(e)}_setTextureSubresources(t){for(const e of t){const{z:i,mipLevel:o}=e;switch(e.type){case"external-image":const{image:s,flipY:r}=e;this.texture.copyExternalImage({image:s,z:i,mipLevel:o,flipY:r});break;case"texture-data":const{data:a,textureFormat:l}=e;if(l&&l!==this.texture.format)throw new Error(`${this} mip level ${o} uses format "${l}" but texture format is "${this.texture.format}"`);this.texture.writeData(a.data,{x:0,y:0,z:i,width:a.width,height:a.height,depthOrArrayLayers:1,mipLevel:o});break;default:throw new Error("Unsupported 2D mip-level payload")}}}async _loadAllData(t){const e=await Ue(t.data);return{dimension:t.dimension??"2d",data:e??null}}_checkNotDestroyed(){this.destroyed&&P.warn(`${this} already destroyed`)}_checkReady(){this.isReady||P.warn(`${this} Cannot perform this operation before ready`)}};y(oe,"defaultProps",{...k.defaultProps,dimension:"2d",data:null,mipmaps:!1});let ot=oe;function Tr(n){if(!n.data)return[];const t=n.width&&n.height?{width:n.width,height:n.height}:void 0,e="format"in n?n.format:void 0;switch(n.dimension){case"1d":return Un();case"2d":return lt(0,n.data,t,e);case"3d":return Dn(n.data);case"2d-array":return jn(n.data);case"cube":return Gn(n.data);case"cube-array":return $n(n.data);default:throw new Error(`Unhandled dimension ${n.dimension}`)}}function Er(n,t,e,i){if(t.length===0)return{subresources:t,mipLevels:1,format:i.format,hasExplicitMipChain:!1};const o=new Map;for(const u of t){const f=o.get(u.z)??[];f.push(u),o.set(u.z,f)}const s=t.some(u=>u.mipLevel>0);let r=i.format,a=Number.POSITIVE_INFINITY;const l=[];for(const[u,f]of o){const d=[...f].sort((b,v)=>b.mipLevel-v.mipLevel),h=d[0];if(!h||h.mipLevel!==0)throw new Error(`DynamicTexture: slice ${u} is missing mip level 0`);const p=Li(n,h);if(p.width!==e.width||p.height!==e.height)throw new Error(`DynamicTexture: slice ${u} base level dimensions ${p.width}x${p.height} do not match expected ${e.width}x${e.height}`);const g=Ci(h);if(g){if(r&&r!==g)throw new Error(`DynamicTexture: slice ${u} base level format "${g}" does not match texture format "${r}"`);r=g}const m=r&&n.isTextureFormatCompressed(r)?Ir(n,p.width,p.height,r):n.getMipLevelCount(p.width,p.height);let x=0;for(let b=0;b<d.length;b++){const v=d[b];if(!v||v.mipLevel!==b||b>=m)break;const _=Li(n,v),C=Math.max(1,p.width>>b),w=Math.max(1,p.height>>b);if(_.width!==C||_.height!==w)break;const I=Ci(v);if(I&&(r||(r=I),I!==r))break;x++,l.push(v)}a=Math.min(a,x)}const c=Number.isFinite(a)?Math.max(1,a):1;return{subresources:l.filter(u=>u.mipLevel<c),mipLevels:c,format:r,hasExplicitMipChain:s}}function Ci(n){if(n.type==="texture-data")return n.textureFormat??Bn(n.data)}function Li(n,t){switch(t.type){case"external-image":return n.getExternalImageSize(t.image);case"texture-data":return{width:t.data.width,height:t.data.height};default:throw new Error("Unsupported texture subresource")}}function Ir(n,t,e,i){const{blockWidth:o=1,blockHeight:s=1}=n.getTextureFormatInfo(i);let r=1;for(let a=1;;a++){const l=Math.max(1,t>>a),c=Math.max(1,e>>a);if(l<o||c<s)break;r++}return r}async function Ue(n){if(n=await n,Array.isArray(n))return await Promise.all(n.map(Ue));if(n&&typeof n=="object"&&n.constructor===Object){const t=n,e=await Promise.all(Object.values(t).map(Ue)),i=Object.keys(t),o={};for(let s=0;s<i.length;s++)o[i[s]]=e[s];return o}return n}const Y=2,Or=1e4,wi="render pipeline initialization failed",se=class se{constructor(t,e){y(this,"device");y(this,"id");y(this,"source");y(this,"vs");y(this,"fs");y(this,"pipelineFactory");y(this,"shaderFactory");y(this,"userData",{});y(this,"parameters");y(this,"topology");y(this,"bufferLayout");y(this,"isInstanced");y(this,"instanceCount",0);y(this,"vertexCount");y(this,"indexBuffer",null);y(this,"bufferAttributes",{});y(this,"constantAttributes",{});y(this,"bindings",{});y(this,"vertexArray");y(this,"transformFeedback",null);y(this,"pipeline");y(this,"shaderInputs");y(this,"material",null);y(this,"_uniformStore");y(this,"_attributeInfos",{});y(this,"_gpuGeometry",null);y(this,"props");y(this,"_pipelineNeedsUpdate","newly created");y(this,"_needsRedraw","initializing");y(this,"_destroyed",!1);y(this,"_lastDrawTimestamp",-1);y(this,"_bindingTable",[]);y(this,"_lastLogTime",0);y(this,"_logOpen",!1);y(this,"_drawCount",0);var l,c,u,f;this.props={...se.defaultProps,...e},e=this.props,this.id=e.id||St("model"),this.device=t,Object.assign(this.userData,e.userData),this.material=e.material||null;const i=Object.fromEntries(((l=this.props.modules)==null?void 0:l.map(d=>[d.name,d]))||[]),o=e.shaderInputs||new br(i,{disableWarnings:this.props.disableWarnings});this.setShaderInputs(o);const s=Mr(t),r=(((c=this.props.modules)==null?void 0:c.length)>0?this.props.modules:(u=this.shaderInputs)==null?void 0:u.getModules())||[];if(this.props.shaderLayout=bi(this.props.shaderLayout,r)||null,this.device.type==="webgpu"&&this.props.source){const{source:d,getUniforms:h,bindingTable:p}=this.props.shaderAssembler.assembleWGSLShader({platformInfo:s,...this.props,modules:r});this.source=d,this._getModuleUniforms=h,this._bindingTable=p;const g=(f=t.getShaderLayout)==null?void 0:f.call(t,this.source);this.props.shaderLayout=bi(this.props.shaderLayout||g||null,r)||null}else{const{vs:d,fs:h,getUniforms:p}=this.props.shaderAssembler.assembleGLSLShaderPair({platformInfo:s,...this.props,modules:r});this.vs=d,this.fs=h,this._getModuleUniforms=p,this._bindingTable=[]}this.vertexCount=this.props.vertexCount,this.instanceCount=this.props.instanceCount,this.topology=this.props.topology,this.bufferLayout=this.props.bufferLayout,this.parameters=this.props.parameters,e.geometry&&this.setGeometry(e.geometry),this.pipelineFactory=e.pipelineFactory||Me.getDefaultPipelineFactory(this.device),this.shaderFactory=e.shaderFactory||Re.getDefaultShaderFactory(this.device),this.pipeline=this._updatePipeline(),this.vertexArray=t.createVertexArray({shaderLayout:this.pipeline.shaderLayout,bufferLayout:this.pipeline.bufferLayout}),this._gpuGeometry&&this._setGeometryAttributes(this._gpuGeometry),"isInstanced"in e&&(this.isInstanced=e.isInstanced),e.instanceCount&&this.setInstanceCount(e.instanceCount),e.vertexCount&&this.setVertexCount(e.vertexCount),e.indexBuffer&&this.setIndexBuffer(e.indexBuffer),e.attributes&&this.setAttributes(e.attributes),e.constantAttributes&&this.setConstantAttributes(e.constantAttributes),e.bindings&&this.setBindings(e.bindings),e.transformFeedback&&(this.transformFeedback=e.transformFeedback)}get[Symbol.toStringTag](){return"Model"}toString(){return`Model(${this.id})`}destroy(){var t;this._destroyed||(this.pipelineFactory.release(this.pipeline),this.shaderFactory.release(this.pipeline.vs),this.pipeline.fs&&this.pipeline.fs!==this.pipeline.vs&&this.shaderFactory.release(this.pipeline.fs),this._uniformStore.destroy(),(t=this._gpuGeometry)==null||t.destroy(),this._destroyed=!0)}needsRedraw(){this._getBindingsUpdateTimestamp()>this._lastDrawTimestamp&&this.setNeedsRedraw("contents of bound textures or buffers updated");const t=this._needsRedraw;return this._needsRedraw=!1,t}setNeedsRedraw(t){this._needsRedraw||(this._needsRedraw=t)}getBindingDebugTable(){return this._bindingTable}predraw(){this.updateShaderInputs(),this.pipeline=this._updatePipeline()}draw(t){const e=this._areBindingsLoading();if(e)return P.info(Y,`>>> DRAWING ABORTED ${this.id}: ${e} not loaded`)(),!1;try{t.pushDebugGroup(`${this}.predraw(${t})`),this.predraw()}finally{t.popDebugGroup()}let i,o=this.pipeline.isErrored;try{if(t.pushDebugGroup(`${this}.draw(${t})`),this._logDrawCallStart(),this.pipeline=this._updatePipeline(),o=this.pipeline.isErrored,o)P.info(Y,`>>> DRAWING ABORTED ${this.id}: ${wi}`)(),i=!1;else{const s=this._getBindings(),r=this._getBindGroups(),{indexBuffer:a}=this.vertexArray,l=a?a.byteLength/(a.indexType==="uint32"?4:2):void 0;i=this.pipeline.draw({renderPass:t,vertexArray:this.vertexArray,isInstanced:this.isInstanced,vertexCount:this.vertexCount,instanceCount:this.instanceCount,indexCount:l,transformFeedback:this.transformFeedback||void 0,bindings:s,bindGroups:r,_bindGroupCacheKeys:this._getBindGroupCacheKeys(),uniforms:this.props.uniforms,parameters:this.parameters,topology:this.topology})}}finally{t.popDebugGroup(),this._logDrawCallEnd()}return this._logFramebuffer(t),i?(this._lastDrawTimestamp=this.device.timestamp,this._needsRedraw=!1):o?this._needsRedraw=wi:this._needsRedraw="waiting for resource initialization",i}setGeometry(t){var i;(i=this._gpuGeometry)==null||i.destroy();const e=t&&sr(this.device,t);if(e){this.setTopology(e.topology||"triangle-list");const o=new Pe(this.bufferLayout);this.bufferLayout=o.mergeBufferLayouts(e.bufferLayout,this.bufferLayout),this.vertexArray&&this._setGeometryAttributes(e)}this._gpuGeometry=e}setTopology(t){t!==this.topology&&(this.topology=t,this._setPipelineNeedsUpdate("topology"))}setBufferLayout(t){const e=new Pe(this.bufferLayout);this.bufferLayout=this._gpuGeometry?e.mergeBufferLayouts(t,this._gpuGeometry.bufferLayout):t,this._setPipelineNeedsUpdate("bufferLayout"),this.pipeline=this._updatePipeline(),this.vertexArray=this.device.createVertexArray({shaderLayout:this.pipeline.shaderLayout,bufferLayout:this.pipeline.bufferLayout}),this._gpuGeometry&&this._setGeometryAttributes(this._gpuGeometry)}setParameters(t){Fe(t,this.parameters,2)||(this.parameters=t,this._setPipelineNeedsUpdate("parameters"))}setInstanceCount(t){this.instanceCount=t,this.isInstanced===void 0&&t>0&&(this.isInstanced=!0),this.setNeedsRedraw("instanceCount")}setVertexCount(t){this.vertexCount=t,this.setNeedsRedraw("vertexCount")}setShaderInputs(t){var e;this.shaderInputs=t,this._uniformStore=new Gs(this.device,this.shaderInputs.modules);for(const[i,o]of Object.entries(this.shaderInputs.modules))if(mr(o)&&!((e=this.material)!=null&&e.ownsModule(i))){const s=this._uniformStore.getManagedUniformBuffer(i);this.bindings[`${i}Uniforms`]=s}this.setNeedsRedraw("shaderInputs")}setMaterial(t){this.material=t,this.setNeedsRedraw("material")}updateShaderInputs(){this._uniformStore.setUniforms(this.shaderInputs.getUniformValues()),this.setBindings(this._getNonMaterialBindings(this.shaderInputs.getBindingValues())),this.setNeedsRedraw("shaderInputs")}setBindings(t){Object.assign(this.bindings,t),this.setNeedsRedraw("bindings")}setTransformFeedback(t){this.transformFeedback=t,this.setNeedsRedraw("transformFeedback")}setIndexBuffer(t){this.vertexArray.setIndexBuffer(t),this.setNeedsRedraw("indexBuffer")}setAttributes(t,e){const i=(e==null?void 0:e.disableWarnings)??this.props.disableWarnings;t.indices&&P.warn(`Model:${this.id} setAttributes() - indexBuffer should be set using setIndexBuffer()`)(),this.bufferLayout=gr(this.pipeline.shaderLayout,this.bufferLayout);const o=new Pe(this.bufferLayout);for(const[s,r]of Object.entries(t)){const a=o.getBufferLayout(s);if(!a){i||P.warn(`Model(${this.id}): Missing layout for buffer "${s}".`)();continue}const l=o.getAttributeNamesForBuffer(a);let c=!1;for(const u of l){const f=this._attributeInfos[u];if(f){const d=this.device.type==="webgpu"?o.getBufferIndex(f.bufferName):f.location;this.vertexArray.setBuffer(d,r),c=!0}}!c&&!i&&P.warn(`Model(${this.id}): Ignoring buffer "${r.id}" for unknown attribute "${s}"`)()}this.setNeedsRedraw("attributes")}setConstantAttributes(t,e){for(const[i,o]of Object.entries(t)){const s=this._attributeInfos[i];s?this.vertexArray.setConstantWebGL(s.location,o):((e==null?void 0:e.disableWarnings)??this.props.disableWarnings)||P.warn(`Model "${this.id}: Ignoring constant supplied for unknown attribute "${i}"`)()}this.setNeedsRedraw("constants")}_areBindingsLoading(){var t;for(const e of Object.values(this.bindings))if(e instanceof ot&&!e.isReady)return e.id;for(const e of Object.values(((t=this.material)==null?void 0:t.bindings)||{}))if(e instanceof ot&&!e.isReady)return e.id;return!1}_getBindings(){const t={};for(const[e,i]of Object.entries(this.bindings))i instanceof ot?i.isReady&&(t[e]=i.texture):t[e]=i;return t}_getBindGroups(){var i;const t=((i=this.pipeline)==null?void 0:i.shaderLayout)||this.props.shaderLayout||{bindings:[]},e=t.bindings.length?$o(t,this._getBindings()):{0:this._getBindings()};if(!this.material)return e;for(const[o,s]of Object.entries(this.material.getBindingsByGroup())){const r=Number(o);e[r]={...e[r]||{},...s}}return e}_getBindGroupCacheKeys(){var e;const t=(e=this.material)==null?void 0:e.getBindGroupCacheKey(3);return t?{3:t}:{}}_getBindingsUpdateTimestamp(){var e;let t=0;for(const i of Object.values(this.bindings))i instanceof Vo?t=Math.max(t,i.texture.updateTimestamp):i instanceof R||i instanceof k?t=Math.max(t,i.updateTimestamp):i instanceof ot?t=i.texture?Math.max(t,i.texture.updateTimestamp):1/0:i instanceof xn||(t=Math.max(t,i.buffer.updateTimestamp));return Math.max(t,((e=this.material)==null?void 0:e.getBindingsUpdateTimestamp())||0)}_setGeometryAttributes(t){const e={...t.attributes};for(const[i]of Object.entries(e))!this.pipeline.shaderLayout.attributes.find(o=>o.name===i)&&i!=="positions"&&delete e[i];this.vertexCount=t.vertexCount,this.setIndexBuffer(t.indices||null),this.setAttributes(t.attributes,{disableWarnings:!0}),this.setAttributes(e,{disableWarnings:this.props.disableWarnings}),this.setNeedsRedraw("geometry attributes")}_setPipelineNeedsUpdate(t){this._pipelineNeedsUpdate||(this._pipelineNeedsUpdate=t),this.setNeedsRedraw(t)}_updatePipeline(){if(this._pipelineNeedsUpdate){let t=null,e=null;this.pipeline&&(P.log(1,`Model ${this.id}: Recreating pipeline because "${this._pipelineNeedsUpdate}".`)(),t=this.pipeline.vs,e=this.pipeline.fs),this._pipelineNeedsUpdate=!1;const i=this.shaderFactory.createShader({id:`${this.id}-vertex`,stage:"vertex",source:this.source||this.vs,debugShaders:this.props.debugShaders});let o=null;this.source?o=i:this.fs&&(o=this.shaderFactory.createShader({id:`${this.id}-fragment`,stage:"fragment",source:this.source||this.fs,debugShaders:this.props.debugShaders})),this.pipeline=this.pipelineFactory.createRenderPipeline({...this.props,bindings:void 0,bufferLayout:this.bufferLayout,topology:this.topology,parameters:this.parameters,bindGroups:this._getBindGroups(),vs:i,fs:o}),this._attributeInfos=Wo(this.pipeline.shaderLayout,this.bufferLayout),t&&this.shaderFactory.release(t),e&&e!==t&&this.shaderFactory.release(e)}return this.pipeline}_logDrawCallStart(){const t=P.level>3?0:Or;P.level<2||Date.now()-this._lastLogTime<t||(this._lastLogTime=Date.now(),this._logOpen=!0,P.group(Y,`>>> DRAWING MODEL ${this.id}`,{collapsed:P.level<=2})())}_logDrawCallEnd(){if(this._logOpen){const t=lr(this.pipeline.shaderLayout,this.id);P.table(Y,t)();const e=this.shaderInputs.getDebugTable();P.table(Y,e)();const i=this._getAttributeDebugTable();P.table(Y,this._attributeInfos)(),P.table(Y,i)(),P.groupEnd(Y)(),this._logOpen=!1}}_logFramebuffer(t){const e=this.device.props.debugFramebuffers;if(this._drawCount++,!e)return;const i=t.props.framebuffer;cr(t,i,{id:(i==null?void 0:i.id)||`${this.id}-framebuffer`,minimap:!0})}_getAttributeDebugTable(){const t={};for(const[e,i]of Object.entries(this._attributeInfos)){const o=this.vertexArray.attributes[i.location];t[i.location]={name:e,type:i.shaderType,values:o?this._getBufferOrConstantValues(o,i.bufferDataType):"null"}}if(this.vertexArray.indexBuffer){const{indexBuffer:e}=this.vertexArray,i=e.indexType==="uint32"?new Uint32Array(e.debugData):new Uint16Array(e.debugData);t.indices={name:"indices",type:e.indexType,values:i.toString()}}return t}_getBufferOrConstantValues(t,e){const i=Ie.getTypedArrayConstructor(e);return(t instanceof R?new i(t.debugData):t).toString()}_getNonMaterialBindings(t){if(!this.material)return t;const e={};for(const[i,o]of Object.entries(t))this.material.ownsBinding(i)||(e[i]=o);return e}};y(se,"defaultProps",{...gt.defaultProps,source:void 0,vs:null,fs:null,id:"unnamed",handle:void 0,userData:{},defines:{},modules:[],geometry:null,indexBuffer:null,attributes:{},constantAttributes:{},bindings:{},uniforms:{},varyings:[],isInstanced:void 0,instanceCount:0,vertexCount:0,shaderInputs:void 0,material:void 0,pipelineFactory:void 0,shaderFactory:void 0,transformFeedback:void 0,shaderAssembler:ns.getDefaultShaderAssembler(),debugShaders:void 0,disableWarnings:void 0});let z=se;function Mr(n){return{type:n.type,shaderLanguage:n.info.shadingLanguage,shaderLanguageVersion:n.info.shadingLanguageVersion,gpu:n.info.gpu,features:n.features}}const xt=class xt{constructor(t,e=xt.defaultProps){y(this,"device");y(this,"model");y(this,"transformFeedback");if(!xt.isSupported(t))throw new Error("BufferTransform not yet implemented on WebGPU");this.device=t,this.model=new z(this.device,{id:e.id||"buffer-transform-model",fs:e.fs||gs(),topology:e.topology||"point-list",varyings:e.outputs||e.varyings,...e}),this.transformFeedback=this.device.createTransformFeedback({layout:this.model.pipeline.shaderLayout,buffers:e.feedbackBuffers}),this.model.setTransformFeedback(this.transformFeedback),Object.seal(this)}static isSupported(t){var e;return((e=t==null?void 0:t.info)==null?void 0:e.type)==="webgl"}destroy(){this.model&&this.model.destroy()}delete(){this.destroy()}run(t){t!=null&&t.inputBuffers&&this.model.setAttributes(t.inputBuffers),t!=null&&t.outputBuffers&&this.transformFeedback.setBuffers(t.outputBuffers);const e=this.device.beginRenderPass(t);this.model.draw(e),e.end()}getBuffer(t){return this.transformFeedback.getBuffer(t)}readAsync(t){const e=this.getBuffer(t);if(!e)throw new Error("BufferTransform#getBuffer");if(e instanceof R)return e.readAsync();const{buffer:i,byteOffset:o=0,byteLength:s=i.byteLength}=e;return i.readAsync(o,s)}};y(xt,"defaultProps",{...z.defaultProps,outputs:void 0,feedbackBuffers:void 0});let bt=xt;class ${constructor(t){y(this,"id");y(this,"topology");y(this,"vertexCount");y(this,"indices");y(this,"attributes");y(this,"userData",{});const{attributes:e={},indices:i=null,vertexCount:o=null}=t;this.id=t.id||St("geometry"),this.topology=t.topology,i&&(this.indices=ArrayBuffer.isView(i)?{value:i,size:1}:i),this.attributes={};for(const[s,r]of Object.entries(e)){const a=ArrayBuffer.isView(r)?{value:r}:r;if(!ArrayBuffer.isView(a.value))throw new Error(`${this._print(s)}: must be typed array or object with value as typed array`);if((s==="POSITION"||s==="positions")&&!a.size&&(a.size=3),s==="indices"){if(this.indices)throw new Error("Multiple indices detected");this.indices=a}else this.attributes[s]=a}this.indices&&this.indices.isIndexed!==void 0&&(this.indices=Object.assign({},this.indices),delete this.indices.isIndexed),this.vertexCount=o||this._calculateVertexCount(this.attributes,this.indices)}getVertexCount(){return this.vertexCount}getAttributes(){return this.indices?{indices:this.indices,...this.attributes}:this.attributes}_print(t){return`Geometry ${this.id} attribute ${t}`}_setAttributes(t,e){return this}_calculateVertexCount(t,e){if(e)return e.value.length;let i=1/0;for(const o of Object.values(t)){const{value:s,size:r,constant:a}=o;!a&&s&&r!==void 0&&r>=1&&(i=Math.min(i,s.length/r))}return i}}class Rr extends ${constructor(t={}){const{id:e=St("cube-geometry"),indices:i=!0}=t;super(i?{...t,id:e,topology:"triangle-list",indices:{size:1,value:zr},attributes:{...jr,...t.attributes}}:{...t,id:e,topology:"triangle-list",indices:void 0,attributes:{...Gr,...t.attributes}})}}const zr=new Uint16Array([0,1,2,0,2,3,4,5,6,4,6,7,8,9,10,8,10,11,12,13,14,12,14,15,16,17,18,16,18,19,20,21,22,20,22,23]),Fr=new Float32Array([-1,-1,1,1,-1,1,1,1,1,-1,1,1,-1,-1,-1,-1,1,-1,1,1,-1,1,-1,-1,-1,1,-1,-1,1,1,1,1,1,1,1,-1,-1,-1,-1,1,-1,-1,1,-1,1,-1,-1,1,1,-1,-1,1,1,-1,1,1,1,1,-1,1,-1,-1,-1,-1,-1,1,-1,1,1,-1,1,-1]),kr=new Float32Array([0,0,1,0,0,1,0,0,1,0,0,1,0,0,-1,0,0,-1,0,0,-1,0,0,-1,0,1,0,0,1,0,0,1,0,0,1,0,0,-1,0,0,-1,0,0,-1,0,0,-1,0,1,0,0,1,0,0,1,0,0,1,0,0,-1,0,0,-1,0,0,-1,0,0,-1,0,0]),Br=new Float32Array([0,0,1,0,1,1,0,1,1,0,1,1,0,1,0,0,0,1,0,0,1,0,1,1,1,1,0,1,0,0,1,0,1,0,1,1,0,1,0,0,0,0,1,0,1,1,0,1]),Nr=new Float32Array([1,-1,1,-1,-1,1,-1,-1,-1,1,-1,-1,1,-1,1,-1,-1,-1,1,1,1,1,-1,1,1,-1,-1,1,1,-1,1,1,1,1,-1,-1,-1,1,1,1,1,1,1,1,-1,-1,1,-1,-1,1,1,1,1,-1,-1,-1,1,-1,1,1,-1,1,-1,-1,-1,-1,-1,-1,1,-1,1,-1,1,1,1,-1,1,1,-1,-1,1,-1,-1,1,1,-1,1,1,1,1,1,-1,-1,-1,-1,-1,-1,1,-1,1,1,-1,1,-1,-1,-1,1,-1]),Ur=new Float32Array([1,1,0,1,0,0,1,0,1,1,0,0,1,1,0,1,0,0,1,0,1,1,0,0,1,1,0,1,0,0,1,0,1,1,0,0,1,1,0,1,0,0,1,0,1,1,0,0,1,1,0,1,0,0,0,0,1,0,1,1,1,1,0,1,0,0,1,0,1,1,0,0]),Dr=new Float32Array([1,0,1,1,0,0,1,1,0,0,0,1,1,0,0,1,1,0,1,1,0,0,0,1,1,1,1,1,1,0,1,1,1,0,0,1,1,1,0,1,1,1,1,1,1,0,0,1,0,1,1,1,1,1,1,1,1,1,0,1,0,1,0,1,0,1,1,1,1,1,0,1,0,0,1,1,0,1,1,1,0,1,0,1,0,0,0,1,0,0,1,1,0,1,0,1,1,1,1,1,0,1,1,1,0,0,1,1,0,0,1,1,1,0,1,1,1,1,1,1,1,0,0,1,0,0,0,1,0,1,0,1,1,1,0,1,1,0,0,1,0,1,0,1]),jr={POSITION:{size:3,value:Fr},NORMAL:{size:3,value:kr},TEXCOORD_0:{size:2,value:Br}},Gr={POSITION:{size:3,value:Nr},TEXCOORD_0:{size:2,value:Ur},COLOR_0:{size:3,value:Dr}};function $r(n){switch(n){case"float64":return Float64Array;case"uint8":case"unorm8":return Uint8ClampedArray;default:return Ho(n)}}const Vr=Ie.getDataType.bind(Ie);function Mt(n,t,e){if(t.size>4)return null;const i=e==="webgpu"&&t.type==="uint8"?"unorm8":t.type;return{attribute:n,format:t.size>1?`${i}x${t.size}`:t.type,byteOffset:t.offset||0}}function et(n){return n.stride||n.size*n.bytesPerElement}function Wr(n,t){return n.type===t.type&&n.size===t.size&&et(n)===et(t)&&(n.offset||0)===(t.offset||0)}function De(n,t){t.offset&&T.removed("shaderAttribute.offset","vertexOffset, elementOffset")();const e=et(n),i=t.vertexOffset!==void 0?t.vertexOffset:n.vertexOffset||0,o=t.elementOffset||0,s=i*e+o*n.bytesPerElement+(n.offset||0);return{...t,offset:s,stride:e}}function Hr(n,t){const e=De(n,t);return{high:e,low:{...e,offset:e.offset+n.size*4}}}class Kr{constructor(t,e,i){this._buffer=null,this.device=t,this.id=e.id||"",this.size=e.size||1;const o=e.logicalType||e.type,s=o==="float64";let{defaultValue:r}=e;r=Number.isFinite(r)?[r]:r||new Array(this.size).fill(0);let a;s?a="float32":!o&&e.isIndexed?a="uint32":a=o||"float32";let l=$r(o||a);this.doublePrecision=s,s&&e.fp64===!1&&(l=Float32Array),this.value=null,this.settings={...e,defaultType:l,defaultValue:r,logicalType:o,type:a,normalized:a.includes("norm"),size:this.size,bytesPerElement:l.BYTES_PER_ELEMENT},this.state={...i,externalBuffer:null,bufferAccessor:this.settings,allocatedValue:null,numInstances:0,bounds:null,constant:!1}}get isConstant(){return this.state.constant}get buffer(){return this._buffer}get byteOffset(){const t=this.getAccessor();return t.vertexOffset?t.vertexOffset*et(t):0}get numInstances(){return this.state.numInstances}set numInstances(t){this.state.numInstances=t}delete(){this._buffer&&(this._buffer.delete(),this._buffer=null),Ht.release(this.state.allocatedValue)}getBuffer(){return this.state.constant?null:this.state.externalBuffer||this._buffer}getValue(t=this.id,e=null){const i={};if(this.state.constant){const o=this.value;if(e){const s=De(this.getAccessor(),e),r=s.offset/o.BYTES_PER_ELEMENT,a=s.size||this.size;i[t]=o.subarray(r,r+a)}else i[t]=o}else i[t]=this.getBuffer();return this.doublePrecision&&(this.value instanceof Float64Array?i[`${t}64Low`]=i[t]:i[`${t}64Low`]=new Float32Array(this.size)),i}_getBufferLayout(t=this.id,e=null){const i=this.getAccessor(),o=[],s={name:this.id,byteStride:et(i)};if(this.doublePrecision){const r=Hr(i,e||{});o.push(Mt(t,{...i,...r.high},this.device.type),Mt(`${t}64Low`,{...i,...r.low},this.device.type))}else if(e){const r=De(i,e);o.push(Mt(t,{...i,...r},this.device.type))}else o.push(Mt(t,i,this.device.type));return s.attributes=o.filter(Boolean),s}setAccessor(t){this.state.bufferAccessor=t}getAccessor(){return this.state.bufferAccessor}getBounds(){if(this.state.bounds)return this.state.bounds;let t=null;if(this.state.constant&&this.value){const e=Array.from(this.value);t=[e,e]}else{const{value:e,numInstances:i,size:o}=this,s=i*o;if(e&&s&&e.length>=s){const r=new Array(o).fill(1/0),a=new Array(o).fill(-1/0);for(let l=0;l<s;)for(let c=0;c<o;c++){const u=e[l++];u<r[c]&&(r[c]=u),u>a[c]&&(a[c]=u)}t=[r,a]}}return this.state.bounds=t,t}setData(t){const{state:e}=this;let i;ArrayBuffer.isView(t)?i={value:t}:t instanceof R?i={buffer:t}:i=t;const o={...this.settings,...i};if(ArrayBuffer.isView(i.value)){if(!i.type)if(this.doublePrecision&&i.value instanceof Float64Array)o.type="float32";else{const r=Vr(i.value);o.type=o.normalized?r.replace("int","norm"):r}o.bytesPerElement=i.value.BYTES_PER_ELEMENT,o.stride=et(o)}if(e.bounds=null,i.constant){let s=i.value;if(s=this._normalizeValue(s,[],0),this.settings.normalized&&(s=this.normalizeConstant(s)),!(!e.constant||!this._areValuesEqual(s,this.value)))return!1;e.externalBuffer=null,e.constant=!0,this.value=ArrayBuffer.isView(s)?s:new Float32Array(s)}else if(i.buffer){const s=i.buffer;e.externalBuffer=s,e.constant=!1,this.value=i.value||null}else if(i.value){this._checkExternalBuffer(i);let s=i.value;e.externalBuffer=null,e.constant=!1,this.value=s;let{buffer:r}=this;const a=et(o),l=(o.vertexOffset||0)*a;if(this.doublePrecision&&s instanceof Float64Array&&(s=ye(s,o)),this.settings.isIndexed){const u=this.settings.defaultType;s.constructor!==u&&(s=new u(s))}const c=s.byteLength+l+a*2;(!r||r.byteLength<c)&&(r=this._createBuffer(c)),r.write(s,l)}return this.setAccessor(o),!0}updateSubBuffer(t={}){this.state.bounds=null;const e=this.value,{startOffset:i=0,endOffset:o}=t;this.buffer.write(this.doublePrecision&&e instanceof Float64Array?ye(e,{size:this.size,startIndex:i,endIndex:o}):e.subarray(i,o),i*e.BYTES_PER_ELEMENT+this.byteOffset)}allocate(t,e=!1){const{state:i}=this,o=i.allocatedValue,s=Ht.allocate(o,t+1,{size:this.size,type:this.settings.defaultType,copy:e});this.value=s;const{byteOffset:r}=this;let{buffer:a}=this;return(!a||a.byteLength<s.byteLength+r)&&(a=this._createBuffer(s.byteLength+r),e&&o&&a.write(o instanceof Float64Array?ye(o,this):o,r)),i.allocatedValue=s,i.constant=!1,i.externalBuffer=null,this.setAccessor(this.settings),!0}_checkExternalBuffer(t){const{value:e}=t;if(!ArrayBuffer.isView(e))throw new Error(`Attribute ${this.id} value is not TypedArray`);const i=this.settings.defaultType;let o=!1;if(this.doublePrecision&&(o=e.BYTES_PER_ELEMENT<4),o)throw new Error(`Attribute ${this.id} does not support ${e.constructor.name}`);!(e instanceof i)&&this.settings.normalized&&!("normalized"in t)&&T.warn(`Attribute ${this.id} is normalized`)()}normalizeConstant(t){switch(this.settings.type){case"snorm8":return new Float32Array(t).map(e=>(e+128)/255*2-1);case"snorm16":return new Float32Array(t).map(e=>(e+32768)/65535*2-1);case"unorm8":return new Float32Array(t).map(e=>e/255);case"unorm16":return new Float32Array(t).map(e=>e/65535);default:return t}}_normalizeValue(t,e,i){const{defaultValue:o,size:s}=this.settings;if(Number.isFinite(t))return e[i]=t,e;if(!t){let r=s;for(;--r>=0;)e[i+r]=o[r];return e}switch(s){case 4:e[i+3]=Number.isFinite(t[3])?t[3]:o[3];case 3:e[i+2]=Number.isFinite(t[2])?t[2]:o[2];case 2:e[i+1]=Number.isFinite(t[1])?t[1]:o[1];case 1:e[i+0]=Number.isFinite(t[0])?t[0]:o[0];break;default:let r=s;for(;--r>=0;)e[i+r]=Number.isFinite(t[r])?t[r]:o[r]}return e}_areValuesEqual(t,e){if(!t||!e)return!1;const{size:i}=this;for(let o=0;o<i;o++)if(t[o]!==e[o])return!1;return!0}_createBuffer(t){var o;this._buffer&&this._buffer.destroy();const{isIndexed:e,type:i}=this.settings;return this._buffer=this.device.createBuffer({...(o=this._buffer)==null?void 0:o.props,id:this.id,usage:(e?R.INDEX:R.VERTEX)|R.COPY_DST,indexType:e?i:void 0,byteLength:t}),this._buffer}}const Ai=[],Si=[];function ct(n,t=0,e=1/0){let i=Ai;const o={index:-1,data:n,target:[]};return n?typeof n[Symbol.iterator]=="function"?i=n:n.length>0&&(Si.length=n.length,i=Si):i=Ai,(t>0||Number.isFinite(e))&&(i=(Array.isArray(i)?i:Array.from(i)).slice(t,e),o.index=t-1),{iterable:i,objectInfo:o}}function Vn(n){return n&&n[Symbol.asyncIterator]}function Wn(n,t){const{size:e,stride:i,offset:o,startIndices:s,nested:r}=t,a=n.BYTES_PER_ELEMENT,l=i?i/a:e,c=o?o/a:0,u=Math.floor((n.length-c)/l);return(f,{index:d,target:h})=>{if(!s){const x=d*l+c;for(let b=0;b<e;b++)h[b]=n[x+b];return h}const p=s[d],g=s[d+1]||u;let m;if(r){m=new Array(g-p);for(let x=p;x<g;x++){const b=x*l+c;h=new Array(e);for(let v=0;v<e;v++)h[v]=n[b+v];m[x-p]=h}}else if(l===e)m=n.subarray(p*e+c,g*e+c);else{m=new n.constructor((g-p)*e);let x=0;for(let b=p;b<g;b++){const v=b*l+c;for(let _=0;_<e;_++)m[x++]=n[v+_]}}return m}}const Yr=[],jt=[[0,1/0]];function Zr(n,t){if(n===jt||(t[0]<0&&(t[0]=0),t[0]>=t[1]))return n;const e=[],i=n.length;let o=0;for(let s=0;s<i;s++){const r=n[s];r[1]<t[0]?(e.push(r),o=s+1):r[0]>t[1]?e.push(r):t=[Math.min(r[0],t[0]),Math.max(r[1],t[1])]}return e.splice(o,0,t),e}const qr={interpolation:{duration:0,easing:n=>n},spring:{stiffness:.05,damping:.5}};function Hn(n,t){if(!n)return null;Number.isFinite(n)&&(n={type:"interpolation",duration:n});const e=n.type||"interpolation";return{...qr[e],...t,...n,type:e}}class Kn extends Kr{constructor(t,e){super(t,e,{startIndices:null,lastExternalBuffer:null,binaryValue:null,binaryAccessor:null,needsUpdate:!0,needsRedraw:!1,layoutChanged:!1,updateRanges:jt}),this.constant=!1,this.settings.update=e.update||(e.accessor?this._autoUpdater:void 0),Object.seal(this.settings),Object.seal(this.state),this._validateAttributeUpdaters()}get startIndices(){return this.state.startIndices}set startIndices(t){this.state.startIndices=t}needsUpdate(){return this.state.needsUpdate}needsRedraw({clearChangedFlags:t=!1}={}){const e=this.state.needsRedraw;return this.state.needsRedraw=e&&!t,e}layoutChanged(){return this.state.layoutChanged}setAccessor(t){var e;(e=this.state).layoutChanged||(e.layoutChanged=!Wr(t,this.getAccessor())),super.setAccessor(t)}getUpdateTriggers(){const{accessor:t}=this.settings;return[this.id].concat(typeof t!="function"&&t||[])}supportsTransition(){return!!this.settings.transition}getTransitionSetting(t){if(!t||!this.supportsTransition())return null;const{accessor:e}=this.settings,i=this.settings.transition,o=Array.isArray(e)?t[e.find(s=>t[s])]:t[e];return Hn(o,i)}setNeedsUpdate(t=this.id,e){if(this.state.needsUpdate=this.state.needsUpdate||t,this.setNeedsRedraw(t),e){const{startRow:i=0,endRow:o=1/0}=e;this.state.updateRanges=Zr(this.state.updateRanges,[i,o])}else this.state.updateRanges=jt}clearNeedsUpdate(){this.state.needsUpdate=!1,this.state.updateRanges=Yr}setNeedsRedraw(t=this.id){this.state.needsRedraw=this.state.needsRedraw||t}allocate(t){const{state:e,settings:i}=this;return i.noAlloc?!1:i.update?(super.allocate(t,e.updateRanges!==jt),!0):!1}updateBuffer({numInstances:t,data:e,props:i,context:o}){if(!this.needsUpdate())return!1;const{state:{updateRanges:s},settings:{update:r,noAlloc:a}}=this;let l=!0;if(r){for(const[c,u]of s)r.call(o,this,{data:e,startRow:c,endRow:u,props:i,numInstances:t});if(this.value)if(this.constant||!this.buffer||this.buffer.byteLength<this.value.byteLength+this.byteOffset)this.constant?this.setConstantValue(o,this.value):this.setData({value:this.value,constant:this.constant}),this.constant=!1;else for(const[c,u]of s){const f=Number.isFinite(c)?this.getVertexOffset(c):0,d=Number.isFinite(u)?this.getVertexOffset(u):a||!Number.isFinite(t)?this.value.length:t*this.size;super.updateSubBuffer({startOffset:f,endOffset:d})}this._checkAttributeArray()}else l=!1;return this.clearNeedsUpdate(),this.setNeedsRedraw(),l}setConstantValue(t,e){if(e===void 0||typeof e=="function")return!1;const i=this.settings.transform&&t?this.settings.transform.call(t,e):e;return this.device.type==="webgpu"?this.setConstantBufferValue(i,this.numInstances):(this.setData({constant:!0,value:i})&&this.setNeedsRedraw(),this.clearNeedsUpdate(),!0)}setConstantBufferValue(t,e){const i=this.settings.defaultType,o=this._normalizeValue(t,new i(this.size),0);if(this._hasConstantBufferValue(o,e))return this.constant=!1,this.clearNeedsUpdate(),!1;const s=new i(Math.max(e,1)*this.size);for(let a=0;a<s.length;a+=this.size)s.set(o,a);const r=this.setData({value:s});return this.constant=!1,this.clearNeedsUpdate(),r&&this.setNeedsRedraw(),r}_hasConstantBufferValue(t,e){const i=this.value,o=Math.max(e,1)*this.size;if(!ArrayBuffer.isView(i)||i.length!==o||i.length%this.size!==0)return!1;for(let s=0;s<i.length;s+=this.size)for(let r=0;r<this.size;r++)if(i[s+r]!==t[r])return!1;return!0}setExternalBuffer(t){const{state:e}=this;return t?(this.clearNeedsUpdate(),e.lastExternalBuffer===t||(e.lastExternalBuffer=t,this.setNeedsRedraw(),this.setData(t)),!0):(e.lastExternalBuffer=null,!1)}setBinaryValue(t,e=null){const{state:i,settings:o}=this;if(!t)return i.binaryValue=null,i.binaryAccessor=null,!1;if(o.noAlloc)return!1;if(i.binaryValue===t)return this.clearNeedsUpdate(),!0;if(i.binaryValue=t,this.setNeedsRedraw(),o.transform||e!==this.startIndices){ArrayBuffer.isView(t)&&(t={value:t});const r=t;Z(ArrayBuffer.isView(r.value),`invalid ${o.accessor}`);const a=!!r.size&&r.size!==this.size;return i.binaryAccessor=Wn(r.value,{size:r.size||this.size,stride:r.stride,offset:r.offset,startIndices:e,nested:a}),!1}return this.clearNeedsUpdate(),this.setData(t),!0}getVertexOffset(t){const{startIndices:e}=this;return(e?t<e.length?e[t]:this.numInstances:t)*this.size}getValue(){const t=this.settings.shaderAttributes,e=super.getValue();if(!t)return e;for(const i in t)Object.assign(e,super.getValue(i,t[i]));return e}getBufferLayout(t){this.state.layoutChanged=!1;const e=this.settings.shaderAttributes,i=super._getBufferLayout(),{stepMode:o}=this.settings;if(o==="dynamic"?i.stepMode=t?t.isInstanced?"instance":"vertex":"instance":i.stepMode=o??"vertex",!e)return i;for(const s in e){const r=super._getBufferLayout(s,e[s]);i.attributes.push(...r.attributes)}return i}_autoUpdater(t,{data:e,startRow:i,endRow:o,props:s,numInstances:r}){const{settings:a,state:l,value:c,size:u,startIndices:f}=t,{accessor:d,transform:h}=a,p=l.binaryAccessor||(typeof d=="function"?d:s[d]);Z(typeof p=="function",`accessor "${d}" is not a function`);let g=t.getVertexOffset(i);const{iterable:m,objectInfo:x}=ct(e,i,o);for(const b of m){x.index++;let v=p(b,x);if(h&&(v=h.call(this,v)),f){const _=(x.index<f.length-1?f[x.index+1]:r)-f[x.index];if(v&&Array.isArray(v[0])){let C=g;for(const w of v)t._normalizeValue(w,c,C),C+=u}else v&&v.length>u?c.set(v,g):(t._normalizeValue(v,x.target,0),os({target:c,source:x.target,start:g,count:_}));g+=_*u}else t._normalizeValue(v,c,g),g+=u}}_validateAttributeUpdaters(){const{settings:t}=this;if(!(t.noAlloc||typeof t.update=="function"))throw new Error(`Attribute ${this.id} missing update or accessor`)}_checkAttributeArray(){const{value:t}=this,e=Math.min(4,this.size);if(t&&t.length>=e){let i=!0;switch(e){case 4:i=i&&Number.isFinite(t[3]);case 3:i=i&&Number.isFinite(t[2]);case 2:i=i&&Number.isFinite(t[1]);case 1:i=i&&Number.isFinite(t[0]);break;default:i=!1}if(!i)throw new Error(`Illegal attribute generated for ${this.id}`)}}}function Ce(n){const{source:t,target:e,start:i=0,size:o,getData:s}=n,r=n.end||e.length,a=t.length,l=r-i;if(a>l){e.set(t.subarray(0,l),i);return}if(e.set(t,i),!s)return;let c=a;for(;c<l;){const u=s(c,t);for(let f=0;f<o;f++)e[i+c]=u[f]||0,c++}}function Xr({source:n,target:t,size:e,getData:i,sourceStartIndices:o,targetStartIndices:s}){if(!o||!s)return Ce({source:n,target:t,size:e,getData:i}),t;let r=0,a=0;const l=i&&((u,f)=>i(u+a,f)),c=Math.min(o.length,s.length);for(let u=1;u<c;u++){const f=o[u]*e,d=s[u]*e;Ce({source:n.subarray(r,f),target:t,start:a,end:d,size:e,getData:l}),r=f,a=d}return a<t.length&&Ce({source:[],target:t,start:a,size:e,getData:l}),t}function Jr(n){const{device:t,settings:e,value:i}=n,o=new Kn(t,e);return o.setData({value:i instanceof Float64Array?new Float64Array(0):new Float32Array(0),normalized:e.normalized}),o}function Yn(n){switch(n){case 1:return"float";case 2:return"vec2";case 3:return"vec3";case 4:return"vec4";default:throw new Error(`No defined attribute type for size "${n}"`)}}function Zn(n){switch(n){case 1:return"float32";case 2:return"float32x2";case 3:return"float32x3";case 4:return"float32x4";default:throw new Error("invalid type size")}}function qn(n){n.push(n.shift())}function Qr(n,t){const{doublePrecision:e,settings:i,value:o,size:s}=n,r=e&&o instanceof Float64Array?2:1;let a=0;const{shaderAttributes:l}=n.settings;if(l)for(const c of Object.values(l))a=Math.max(a,c.vertexOffset??0);return(i.noAlloc?o.length:(t+a)*s)*r}function Xn({device:n,source:t,target:e}){return(!e||e.byteLength<t.byteLength)&&(e==null||e.destroy(),e=n.createBuffer({byteLength:t.byteLength,usage:t.usage})),e}function Jn({device:n,buffer:t,attribute:e,fromLength:i,toLength:o,fromStartIndices:s,getData:r=a=>a}){const a=e.doublePrecision&&e.value instanceof Float64Array?2:1,l=e.size*a,c=e.byteOffset,u=e.settings.bytesPerElement<4?c/e.settings.bytesPerElement*4:c,f=e.startIndices,d=s&&f,h=e.isConstant;if(!d&&t&&i>=o)return t;const p=e.value instanceof Float64Array?Float32Array:e.value.constructor,g=h?e.value:new p(e.getBuffer().readSyncWebGL(c,o*p.BYTES_PER_ELEMENT).buffer);if(e.settings.normalized&&!h){const v=r;r=(_,C)=>e.normalizeConstant(v(_,C))}const m=h?(v,_)=>r(g,_):(v,_)=>r(g.subarray(v+c,v+c+l),_),x=t?new Float32Array(t.readSyncWebGL(u,i*4).buffer):new Float32Array(0),b=new Float32Array(o);return Xr({source:x,target:b,sourceStartIndices:s,targetStartIndices:f,size:l,getData:m}),(!t||t.byteLength<b.byteLength+u)&&(t==null||t.destroy(),t=n.createBuffer({byteLength:b.byteLength+u,usage:35050})),t.write(b,u),t}class Qn{constructor({device:t,attribute:e,timeline:i}){this.buffers=[],this.currentLength=0,this.device=t,this.transition=new Xe(i),this.attribute=e,this.attributeInTransition=Jr(e),this.currentStartIndices=e.startIndices}get inProgress(){return this.transition.inProgress}start(t,e,i=1/0){this.settings=t,this.currentStartIndices=this.attribute.startIndices,this.currentLength=Qr(this.attribute,e),this.transition.start({...t,duration:i})}update(){const t=this.transition.update();return t&&this.onUpdate(),t}setBuffer(t){this.attributeInTransition.setData({buffer:t,normalized:this.attribute.settings.normalized,value:this.attributeInTransition.value})}cancel(){this.transition.cancel()}delete(){this.cancel();for(const t of this.buffers)t.destroy();this.buffers.length=0}}class ta extends Qn{constructor({device:t,attribute:e,timeline:i}){super({device:t,attribute:e,timeline:i}),this.type="interpolation",this.transform=oa(t,e)}start(t,e){const i=this.currentLength,o=this.currentStartIndices;if(super.start(t,e,t.duration),t.duration<=0){this.transition.cancel();return}const{buffers:s,attribute:r}=this;qn(s),s[0]=Jn({device:this.device,buffer:s[0],attribute:r,fromLength:i,toLength:this.currentLength,fromStartIndices:o,getData:t.enter}),s[1]=Xn({device:this.device,source:s[0],target:s[1]}),this.setBuffer(s[1]);const{transform:a}=this,l=a.model;let c=Math.floor(this.currentLength/r.size);to(r)&&(c/=2),l.setVertexCount(c),r.isConstant?(l.setAttributes({aFrom:s[0]}),l.setConstantAttributes({aTo:r.value})):l.setAttributes({aFrom:s[0],aTo:r.getBuffer()}),a.transformFeedback.setBuffers({vCurrent:s[1]})}onUpdate(){const{duration:t,easing:e}=this.settings,{time:i}=this.transition;let o=i/t;e&&(o=e(o));const{model:s}=this.transform,r={time:o};s.shaderInputs.setProps({interpolation:r}),this.transform.run({discard:!0})}delete(){super.delete(),this.transform.destroy()}}const ea=`layout(std140) uniform interpolationUniforms {
  float time;
} interpolation;
`,Ti={name:"interpolation",vs:ea,uniformTypes:{time:"f32"}},ia=`#version 300 es
#define SHADER_NAME interpolation-transition-vertex-shader

in ATTRIBUTE_TYPE aFrom;
in ATTRIBUTE_TYPE aTo;
out ATTRIBUTE_TYPE vCurrent;

void main(void) {
  vCurrent = mix(aFrom, aTo, interpolation.time);
  gl_Position = vec4(0.0);
}
`,na=`#version 300 es
#define SHADER_NAME interpolation-transition-vertex-shader

in ATTRIBUTE_TYPE aFrom;
in ATTRIBUTE_TYPE aFrom64Low;
in ATTRIBUTE_TYPE aTo;
in ATTRIBUTE_TYPE aTo64Low;
out ATTRIBUTE_TYPE vCurrent;
out ATTRIBUTE_TYPE vCurrent64Low;

vec2 mix_fp64(vec2 a, vec2 b, float x) {
  vec2 range = sub_fp64(b, a);
  return sum_fp64(a, mul_fp64(range, vec2(x, 0.0)));
}

void main(void) {
  for (int i=0; i<ATTRIBUTE_SIZE; i++) {
    vec2 value = mix_fp64(vec2(aFrom[i], aFrom64Low[i]), vec2(aTo[i], aTo64Low[i]), interpolation.time);
    vCurrent[i] = value.x;
    vCurrent64Low[i] = value.y;
  }
  gl_Position = vec4(0.0);
}
`;function to(n){return n.doublePrecision&&n.value instanceof Float64Array}function oa(n,t){const e=t.size,i=Yn(e),o=Zn(e),s=t.getBufferLayout();return to(t)?new bt(n,{vs:na,bufferLayout:[{name:"aFrom",byteStride:8*e,attributes:[{attribute:"aFrom",format:o,byteOffset:0},{attribute:"aFrom64Low",format:o,byteOffset:4*e}]},{name:"aTo",byteStride:8*e,attributes:[{attribute:"aTo",format:o,byteOffset:0},{attribute:"aTo64Low",format:o,byteOffset:4*e}]}],modules:[Cs,Ti],defines:{ATTRIBUTE_TYPE:i,ATTRIBUTE_SIZE:e},moduleSettings:{},varyings:["vCurrent","vCurrent64Low"],bufferMode:35980,disableWarnings:!0}):new bt(n,{vs:ia,bufferLayout:[{name:"aFrom",format:o},{name:"aTo",format:s.attributes[0].format}],modules:[Ti],defines:{ATTRIBUTE_TYPE:i},varyings:["vCurrent"],disableWarnings:!0})}class sa extends Qn{constructor({device:t,attribute:e,timeline:i}){super({device:t,attribute:e,timeline:i}),this.type="spring",this.texture=fa(t),this.framebuffer=da(t,this.texture),this.transform=ua(t,e)}start(t,e){const i=this.currentLength,o=this.currentStartIndices;super.start(t,e);const{buffers:s,attribute:r}=this;for(let l=0;l<2;l++)s[l]=Jn({device:this.device,buffer:s[l],attribute:r,fromLength:i,toLength:this.currentLength,fromStartIndices:o,getData:t.enter});s[2]=Xn({device:this.device,source:s[0],target:s[2]}),this.setBuffer(s[1]);const{model:a}=this.transform;a.setVertexCount(Math.floor(this.currentLength/r.size)),r.isConstant?a.setConstantAttributes({aTo:r.value}):a.setAttributes({aTo:r.getBuffer()})}onUpdate(){const{buffers:t,transform:e,framebuffer:i,transition:o}=this,s=this.settings;e.model.setAttributes({aPrev:t[0],aCur:t[1]}),e.transformFeedback.setBuffers({vNext:t[2]});const r={stiffness:s.stiffness,damping:s.damping};e.model.shaderInputs.setProps({spring:r}),e.run({framebuffer:i,discard:!1,parameters:{viewport:[0,0,1,1]},clearColor:[0,0,0,0]}),qn(t),this.setBuffer(t[1]),this.device.readPixelsToArrayWebGL(i)[0]>0||o.end()}delete(){super.delete(),this.transform.destroy(),this.texture.destroy(),this.framebuffer.destroy()}}const ra=`layout(std140) uniform springUniforms {
  float damping;
  float stiffness;
} spring;
`,aa={name:"spring",vs:ra,uniformTypes:{damping:"f32",stiffness:"f32"}},la=`#version 300 es
#define SHADER_NAME spring-transition-vertex-shader

#define EPSILON 0.00001

in ATTRIBUTE_TYPE aPrev;
in ATTRIBUTE_TYPE aCur;
in ATTRIBUTE_TYPE aTo;
out ATTRIBUTE_TYPE vNext;
out float vIsTransitioningFlag;

ATTRIBUTE_TYPE getNextValue(ATTRIBUTE_TYPE cur, ATTRIBUTE_TYPE prev, ATTRIBUTE_TYPE dest) {
  ATTRIBUTE_TYPE velocity = cur - prev;
  ATTRIBUTE_TYPE delta = dest - cur;
  ATTRIBUTE_TYPE force = delta * spring.stiffness;
  ATTRIBUTE_TYPE resistance = velocity * spring.damping;
  return force - resistance + velocity + cur;
}

void main(void) {
  bool isTransitioning = length(aCur - aPrev) > EPSILON || length(aTo - aCur) > EPSILON;
  vIsTransitioningFlag = isTransitioning ? 1.0 : 0.0;

  vNext = getNextValue(aCur, aPrev, aTo);
  gl_Position = vec4(0, 0, 0, 1);
  gl_PointSize = 100.0;
}
`,ca=`#version 300 es
#define SHADER_NAME spring-transition-is-transitioning-fragment-shader

in float vIsTransitioningFlag;

out vec4 fragColor;

void main(void) {
  if (vIsTransitioningFlag == 0.0) {
    discard;
  }
  fragColor = vec4(1.0);
}`;function ua(n,t){const e=Yn(t.size),i=Zn(t.size);return new bt(n,{vs:la,fs:ca,bufferLayout:[{name:"aPrev",format:i},{name:"aCur",format:i},{name:"aTo",format:t.getBufferLayout().attributes[0].format}],varyings:["vNext"],modules:[aa],defines:{ATTRIBUTE_TYPE:e},parameters:{depthCompare:"always",blendColorOperation:"max",blendColorSrcFactor:"one",blendColorDstFactor:"one",blendAlphaOperation:"max",blendAlphaSrcFactor:"one",blendAlphaDstFactor:"one"}})}function fa(n){return n.createTexture({data:new Uint8Array(4),format:"rgba8unorm",width:1,height:1})}function da(n,t){return n.createFramebuffer({id:"spring-transition-is-transitioning-framebuffer",width:1,height:1,colorAttachments:[t]})}const ha={interpolation:ta,spring:sa};class pa{constructor(t,{id:e,timeline:i}){if(!t)throw new Error("AttributeTransitionManager is constructed without device");this.id=e,this.device=t,this.timeline=i,this.transitions={},this.needsRedraw=!1,this.numInstances=1}finalize(){for(const t in this.transitions)this._removeTransition(t)}update({attributes:t,transitions:e,numInstances:i}){this.numInstances=i||1;for(const o in t){const s=t[o],r=s.getTransitionSetting(e);r&&this._updateAttribute(o,s,r)}for(const o in this.transitions){const s=t[o];(!s||!s.getTransitionSetting(e))&&this._removeTransition(o)}}hasAttribute(t){const e=this.transitions[t];return e&&e.inProgress}getAttributes(){const t={};for(const e in this.transitions){const i=this.transitions[e];i.inProgress&&(t[e]=i.attributeInTransition)}return t}run(){if(this.numInstances===0)return!1;for(const e in this.transitions)this.transitions[e].update()&&(this.needsRedraw=!0);const t=this.needsRedraw;return this.needsRedraw=!1,t}_removeTransition(t){this.transitions[t].delete(),delete this.transitions[t]}_updateAttribute(t,e,i){const o=this.transitions[t];let s=!o||o.type!==i.type;if(s){o&&this._removeTransition(t);const r=ha[i.type];r?this.transitions[t]=new r({attribute:e,timeline:this.timeline,device:this.device}):(T.error(`unsupported transition type '${i.type}'`)(),s=!1)}(s||e.needsRedraw())&&(this.needsRedraw=!0,this.transitions[t].start(i,this.numInstances))}}const Ei="attributeManager.invalidate",ga="attributeManager.updateStart",ma="attributeManager.updateEnd",ya="attribute.updateStart",va="attribute.allocate",_a="attribute.updateEnd";class xa{constructor(t,{id:e="attribute-manager",stats:i,timeline:o}={}){this.mergeBoundsMemoized=bn(ss),this.id=e,this.device=t,this.attributes={},this.updateTriggers={},this.needsRedraw=!0,this.userData={},this.stats=i,this.attributeTransitionManager=new pa(t,{id:`${e}-transitions`,timeline:o}),Object.seal(this)}finalize(){for(const t in this.attributes)this.attributes[t].delete();this.attributeTransitionManager.finalize()}getNeedsRedraw(t={clearRedrawFlags:!1}){const e=this.needsRedraw;return this.needsRedraw=this.needsRedraw&&!t.clearRedrawFlags,e&&this.id}setNeedsRedraw(){this.needsRedraw=!0}add(t){this._add(t)}addInstanced(t){this._add(t,{stepMode:"instance"})}remove(t){for(const e of t)this.attributes[e]!==void 0&&(this.attributes[e].delete(),delete this.attributes[e])}invalidate(t,e){const i=this._invalidateTrigger(t,e);B(Ei,this,t,i)}invalidateAll(t){for(const e in this.attributes)this.attributes[e].setNeedsUpdate(e,t);B(Ei,this,"all")}update({data:t,numInstances:e,startIndices:i=null,transitions:o,props:s={},buffers:r={},context:a={}}){let l=!1;B(ga,this),this.stats&&this.stats.get("Update Attributes").timeStart();for(const c in this.attributes){const u=this.attributes[c],f=u.settings.accessor;u.startIndices=i,u.numInstances=e,s[c]&&T.removed(`props.${c}`,`data.attributes.${c}`)(),u.setExternalBuffer(r[c])||u.setBinaryValue(typeof f=="string"?r[f]:void 0,t.startIndices)||typeof f=="string"&&!r[f]&&u.setConstantValue(a,s[f])||u.needsUpdate()&&(l=!0,this._updateAttribute({attribute:u,numInstances:e,data:t,props:s,context:a})),this.needsRedraw=this.needsRedraw||u.needsRedraw()}l&&B(ma,this,e),this.stats&&(this.stats.get("Update Attributes").timeEnd(),l&&this.stats.get("Attributes updated").incrementCount()),this.attributeTransitionManager.update({attributes:this.attributes,numInstances:e,transitions:o})}updateTransition(){const{attributeTransitionManager:t}=this,e=t.run();return this.needsRedraw=this.needsRedraw||e,e}getAttributes(){return{...this.attributes,...this.attributeTransitionManager.getAttributes()}}getBounds(t){const e=t.map(i=>{var o;return(o=this.attributes[i])==null?void 0:o.getBounds()});return this.mergeBoundsMemoized(e)}getChangedAttributes(t={clearChangedFlags:!1}){const{attributes:e,attributeTransitionManager:i}=this,o={...i.getAttributes()};for(const s in e){const r=e[s];r.needsRedraw(t)&&!i.hasAttribute(s)&&(o[s]=r)}return o}getBufferLayouts(t){return Object.values(this.getAttributes()).map(e=>e.getBufferLayout(t))}_add(t,e){for(const i in t){const o=t[i],s={...o,id:i,size:o.isIndexed&&1||o.size||1,...e};this.attributes[i]=new Kn(this.device,s)}this._mapUpdateTriggersToAttributes()}_mapUpdateTriggersToAttributes(){const t={};for(const e in this.attributes)this.attributes[e].getUpdateTriggers().forEach(o=>{t[o]||(t[o]=[]),t[o].push(e)});this.updateTriggers=t}_invalidateTrigger(t,e){const{attributes:i,updateTriggers:o}=this,s=o[t];return s&&s.forEach(r=>{const a=i[r];a&&a.setNeedsUpdate(a.id,e)}),s}_updateAttribute(t){const{attribute:e,numInstances:i}=t;if(B(ya,e),e.constant){e.setConstantValue(t.context,e.value);return}e.allocate(i)&&B(va,e,i),e.updateBuffer(t)&&(this.needsRedraw=!0,B(_a,e,i))}}class ba extends Xe{get value(){return this._value}_onUpdate(){const{time:t,settings:{fromValue:e,toValue:i,duration:o,easing:s}}=this,r=s(t/o);this._value=Ut(e,i,r)}}const Ii=1e-5;function Oi(n,t,e,i,o){const s=t-n,a=(e-t)*o,l=-s*i;return a+l+s+t}function Pa(n,t,e,i,o){if(Array.isArray(e)){const s=[];for(let r=0;r<e.length;r++)s[r]=Oi(n[r],t[r],e[r],i,o);return s}return Oi(n,t,e,i,o)}function Mi(n,t){if(Array.isArray(n)){let e=0;for(let i=0;i<n.length;i++){const o=n[i]-t[i];e+=o*o}return Math.sqrt(e)}return Math.abs(n-t)}class Ca extends Xe{get value(){return this._currValue}_onUpdate(){const{fromValue:t,toValue:e,damping:i,stiffness:o}=this.settings,{_prevValue:s=t,_currValue:r=t}=this;let a=Pa(s,r,e,i,o);const l=Mi(a,e),c=Mi(a,r);l<Ii&&c<Ii&&(a=e,this.end()),this._prevValue=r,this._currValue=a}}const La={interpolation:ba,spring:Ca};class wa{constructor(t){this.transitions=new Map,this.timeline=t}get active(){return this.transitions.size>0}add(t,e,i,o){const{transitions:s}=this;if(s.has(t)){const l=s.get(t),{value:c=l.settings.fromValue}=l;e=c,this.remove(t)}if(o=Hn(o),!o)return;const r=La[o.type];if(!r){T.error(`unsupported transition type '${o.type}'`)();return}const a=new r(this.timeline);a.start({...o,fromValue:e,toValue:i}),s.set(t,a)}remove(t){const{transitions:e}=this;e.has(t)&&(e.get(t).cancel(),e.delete(t))}update(){const t={};for(const[e,i]of this.transitions)i.update(),t[e]=i.value,i.inProgress||this.remove(e);return t}clear(){for(const t of this.transitions.keys())this.remove(t)}}function Aa(n){const t=n[J];for(const e in t){const i=t[e],{validate:o}=i;if(o&&!o(n[e],i))throw new Error(`Invalid prop ${e}: ${n[e]}`)}}function Sa(n,t){const e=eo({newProps:n,oldProps:t,propTypes:n[J],ignoreProps:{data:null,updateTriggers:null,extensions:null,transitions:null}}),i=Ea(n,t);let o=!1;return i||(o=Ia(n,t)),{dataChanged:i,propsChanged:e,updateTriggersChanged:o,extensionsChanged:Oa(n,t),transitionsChanged:Ta(n,t)}}function Ta(n,t){if(!n.transitions)return!1;const e={},i=n[J];let o=!1;for(const s in n.transitions){const r=i[s],a=r&&r.type;(a==="number"||a==="color"||a==="array")&&je(n[s],t[s],r)&&(e[s]=!0,o=!0)}return o?e:!1}function eo({newProps:n,oldProps:t,ignoreProps:e={},propTypes:i={},triggerName:o="props"}){if(t===n)return!1;if(typeof n!="object"||n===null)return`${o} changed shallowly`;if(typeof t!="object"||t===null)return`${o} changed shallowly`;for(const s of Object.keys(n))if(!(s in e)){if(!(s in t))return`${o}.${s} added`;const r=je(n[s],t[s],i[s]);if(r)return`${o}.${s} ${r}`}for(const s of Object.keys(t))if(!(s in e)){if(!(s in n))return`${o}.${s} dropped`;if(!Object.hasOwnProperty.call(n,s)){const r=je(n[s],t[s],i[s]);if(r)return`${o}.${s} ${r}`}}return!1}function je(n,t,e){let i=e&&e.equal;return i&&!i(n,t,e)||!i&&(i=n&&t&&n.equals,i&&!i.call(n,t))?"changed deeply":!i&&t!==n?"changed shallowly":null}function Ea(n,t){if(t===null)return"oldProps is null, initial diff";let e=!1;const{dataComparator:i,_dataDiff:o}=n;return i?i(n.data,t.data)||(e="Data comparator detected a change"):n.data!==t.data&&(e="A new data container was supplied"),e&&o&&(e=o(n.data,t.data)||e),e}function Ia(n,t){if(t===null)return{all:!0};if("all"in n.updateTriggers&&Ri(n,t,"all"))return{all:!0};const e={};let i=!1;for(const o in n.updateTriggers)o!=="all"&&Ri(n,t,o)&&(e[o]=!0,i=!0);return i?e:!1}function Oa(n,t){if(t===null)return!0;const e=t.extensions,{extensions:i}=n;if(i===e)return!1;if(!e||!i||i.length!==e.length)return!0;for(let o=0;o<i.length;o++)if(!i[o].equals(e[o]))return!0;return!1}function Ri(n,t,e){let i=n.updateTriggers[e];i=i??{};let o=t.updateTriggers[e];return o=o??{},eo({oldProps:o,newProps:i,triggerName:e})}const Ma="count(): argument not an object",Ra="count(): argument not a container";function za(n){if(!ka(n))throw new Error(Ma);if(typeof n.count=="function")return n.count();if(Number.isFinite(n.size))return n.size;if(Number.isFinite(n.length))return n.length;if(Fa(n))return Object.keys(n).length;throw new Error(Ra)}function Fa(n){return n!==null&&typeof n=="object"&&n.constructor===Object}function ka(n){return n!==null&&typeof n=="object"}function zi(n,t){if(!t)return n;const e={...n,...t};if("defines"in t&&(e.defines={...n.defines,...t.defines}),"modules"in t&&(e.modules=(n.modules||[]).concat(t.modules),t.modules.some(i=>i.name==="project64"))){const i=e.modules.findIndex(o=>o.name==="project32");i>=0&&e.modules.splice(i,1)}if("inject"in t)if(!n.inject)e.inject=t.inject;else{const i={...n.inject};for(const o in t.inject)i[o]=(i[o]||"")+t.inject[o];e.inject=i}return e}const Ba={minFilter:"linear",mipmapFilter:"linear",magFilter:"linear",addressModeU:"clamp-to-edge",addressModeV:"clamp-to-edge"},Ge={};function Na(n,t,e,i){if(e instanceof k)return e;e.constructor&&e.constructor.name!=="Object"&&(e={data:e});let o=null;e.compressed&&(o={minFilter:"linear",mipmapFilter:e.data.length>1?"nearest":"linear"});const{width:s,height:r}=e.data,a=t.createTexture({...e,sampler:{...Ba,...o,...i},mipLevels:t.getMipLevelCount(s,r)});return t.type==="webgl"?a.generateMipmapsWebGL():t.type==="webgpu"&&t.generateMipmapsWebGPU(a),Ge[a.id]=n,a}function Ua(n,t){!t||!(t instanceof k)||Ge[t.id]===n&&(t.delete(),delete Ge[t.id])}const Da={boolean:{validate(n,t){return!0},equal(n,t,e){return!!n==!!t}},number:{validate(n,t){return Number.isFinite(n)&&(!("max"in t)||n<=t.max)&&(!("min"in t)||n>=t.min)}},color:{validate(n,t){return t.optional&&!n||$e(n)&&(n.length===3||n.length===4)},equal(n,t,e){return Et(n,t,1)}},accessor:{validate(n,t){const e=qt(n);return e==="function"||e===qt(t.value)},equal(n,t,e){return typeof t=="function"?!0:Et(n,t,1)}},array:{validate(n,t){return t.optional&&!n||$e(n)},equal(n,t,e){const{compare:i}=e,o=Number.isInteger(i)?i:i?1:0;return i?Et(n,t,o):n===t}},object:{equal(n,t,e){if(e.ignore)return!0;const{compare:i}=e,o=Number.isInteger(i)?i:i?1:0;return i?Et(n,t,o):n===t}},function:{validate(n,t){return t.optional&&!n||typeof n=="function"},equal(n,t,e){return!e.compare&&e.ignore!==!1||n===t}},data:{transform:(n,t,e)=>{if(!n)return n;const{dataTransform:i}=e.props;return i?i(n):typeof n.shape=="string"&&n.shape.endsWith("-table")&&Array.isArray(n.data)?n.data:n}},image:{transform:(n,t,e)=>{const i=e.context;return!i||!i.device?null:Na(e.id,i.device,n,{...t.parameters,...e.props.textureParameters})},release:(n,t,e)=>{Ua(e.id,n)}}};function ja(n){const t={},e={},i={};for(const[o,s]of Object.entries(n)){const r=s==null?void 0:s.deprecatedFor;if(r)i[o]=Array.isArray(r)?r:[r];else{const a=Ga(o,s);t[o]=a,e[o]=a.value}}return{propTypes:t,defaultProps:e,deprecatedProps:i}}function Ga(n,t){switch(qt(t)){case"object":return ht(n,t);case"array":return ht(n,{type:"array",value:t,compare:!1});case"boolean":return ht(n,{type:"boolean",value:t});case"number":return ht(n,{type:"number",value:t});case"function":return ht(n,{type:"function",value:t,compare:!0});default:return{name:n,type:"unknown",value:t}}}function ht(n,t){return"type"in t?{name:n,...Da[t.type],...t}:"value"in t?{name:n,type:qt(t.value),...t}:{name:n,type:"object",value:t}}function $e(n){return Array.isArray(n)||ArrayBuffer.isView(n)}function qt(n){return $e(n)?"array":n===null?"null":typeof n}function $a(n,t){let e;for(let s=t.length-1;s>=0;s--){const r=t[s];"extensions"in r&&(e=r.extensions)}const i=Ve(n.constructor,e),o=Object.create(i);o[Kt]=n,o[it]={},o[q]={};for(let s=0;s<t.length;++s){const r=t[s];for(const a in r)o[a]=r[a]}return Object.freeze(o),o}const Va="_mergedDefaultProps";function Ve(n,t){if(!(n instanceof ce.constructor))return{};let e=Va;if(t)for(const o of t){const s=o.constructor;s&&(e+=`:${s.extensionName||s.name}`)}const i=io(n,e);return i||(n[e]=Wa(n,t||[]))}function Wa(n,t){if(!n.prototype)return null;const i=Object.getPrototypeOf(n),o=Ve(i),s=io(n,"defaultProps")||{},r=ja(s),a=Object.assign(Object.create(null),o,r.defaultProps),l=Object.assign(Object.create(null),o==null?void 0:o[J],r.propTypes),c=Object.assign(Object.create(null),o==null?void 0:o[ve],r.deprecatedProps);for(const u of t){const f=Ve(u.constructor);f&&(Object.assign(a,f),Object.assign(l,f[J]),Object.assign(c,f[ve]))}return Ha(a,n),Ya(a,l),Ka(a,c),a[J]=l,a[ve]=c,t.length===0&&!Qe(n,"_propTypes")&&(n._propTypes=l),a}function Ha(n,t){const e=qa(t);Object.defineProperties(n,{id:{writable:!0,value:e}})}function Ka(n,t){for(const e in t)Object.defineProperty(n,e,{enumerable:!1,set(i){const o=`${this.id}: ${e}`;for(const s of t[e])Qe(this,s)||(this[s]=i);T.deprecated(o,t[e].join("/"))()}})}function Ya(n,t){const e={},i={};for(const o in t){const s=t[o],{name:r,value:a}=s;s.async&&(e[r]=a,i[r]=Za(r))}n[rt]=e,n[it]={},Object.defineProperties(n,i)}function Za(n){return{enumerable:!0,set(t){typeof t=="string"||t instanceof Promise||Vn(t)?this[it][n]=t:this[q][n]=t},get(){if(this[q]){if(n in this[q])return this[q][n]||this[rt][n];if(n in this[it]){const t=this[Kt]&&this[Kt].internalState;if(t&&t.hasAsyncProp(n))return t.getAsyncProp(n)||this[rt][n]}}return this[rt][n]}}}function Qe(n,t){return Object.prototype.hasOwnProperty.call(n,t)}function io(n,t){return Qe(n,t)&&n[t]}function qa(n){const t=n.componentName;return t||T.warn(`${n.name}.componentName not specified`)(),t||n.name}let Xa=0;class ce{constructor(...t){this.props=$a(this,t),this.id=this.props.id,this.count=Xa++}clone(t){const{props:e}=this,i={};for(const o in e[rt])o in e[q]?i[o]=e[q][o]:o in e[it]&&(i[o]=e[it][o]);return new this.constructor({...e,...i,...t})}}ce.componentName="Component";ce.defaultProps={};const Ja=Object.freeze({});class Qa{constructor(t){this.component=t,this.asyncProps={},this.onAsyncPropUpdated=()=>{},this.oldProps=null,this.oldAsyncProps=null}finalize(){for(const t in this.asyncProps){const e=this.asyncProps[t];e&&e.type&&e.type.release&&e.type.release(e.resolvedValue,e.type,this.component)}this.asyncProps={},this.component=null,this.resetOldProps()}getOldProps(){return this.oldAsyncProps||this.oldProps||Ja}resetOldProps(){this.oldAsyncProps=null,this.oldProps=this.component?this.component.props:null}hasAsyncProp(t){return t in this.asyncProps}getAsyncProp(t){const e=this.asyncProps[t];return e&&e.resolvedValue}isAsyncPropLoading(t){if(t){const e=this.asyncProps[t];return!!(e&&e.pendingLoadCount>0&&e.pendingLoadCount!==e.resolvedLoadCount)}for(const e in this.asyncProps)if(this.isAsyncPropLoading(e))return!0;return!1}reloadAsyncProp(t,e){this._watchPromise(t,Promise.resolve(e))}setAsyncProps(t){this.component=t[Kt]||this.component;const e=t[q]||{},i=t[it]||t,o=t[rt]||{};for(const s in e){const r=e[s];this._createAsyncPropData(s,o[s]),this._updateAsyncProp(s,r),e[s]=this.getAsyncProp(s)}for(const s in i){const r=i[s];this._createAsyncPropData(s,o[s]),this._updateAsyncProp(s,r)}}_fetch(t,e){return null}_onResolve(t,e){}_onError(t,e){}_updateAsyncProp(t,e){if(this._didAsyncInputValueChange(t,e)){if(typeof e=="string"&&(e=this._fetch(t,e)),e instanceof Promise){this._watchPromise(t,e);return}if(Vn(e)){this._resolveAsyncIterable(t,e);return}this._setPropValue(t,e)}}_freezeAsyncOldProps(){if(!this.oldAsyncProps&&this.oldProps){this.oldAsyncProps=Object.create(this.oldProps);for(const t in this.asyncProps)Object.defineProperty(this.oldAsyncProps,t,{enumerable:!0,value:this.oldProps[t]})}}_didAsyncInputValueChange(t,e){const i=this.asyncProps[t];return e===i.resolvedValue||e===i.lastValue?!1:(i.lastValue=e,!0)}_setPropValue(t,e){this._freezeAsyncOldProps();const i=this.asyncProps[t];i&&(e=this._postProcessValue(i,e),i.resolvedValue=e,i.pendingLoadCount++,i.resolvedLoadCount=i.pendingLoadCount)}_setAsyncPropValue(t,e,i){const o=this.asyncProps[t];o&&i>=o.resolvedLoadCount&&e!==void 0&&(this._freezeAsyncOldProps(),o.resolvedValue=e,o.resolvedLoadCount=i,this.onAsyncPropUpdated(t,e))}_watchPromise(t,e){const i=this.asyncProps[t];if(i){i.pendingLoadCount++;const o=i.pendingLoadCount;e.then(s=>{this.component&&(s=this._postProcessValue(i,s),this._setAsyncPropValue(t,s,o),this._onResolve(t,s))}).catch(s=>{this._onError(t,s)})}}async _resolveAsyncIterable(t,e){if(t!=="data"){this._setPropValue(t,e);return}const i=this.asyncProps[t];if(!i)return;i.pendingLoadCount++;const o=i.pendingLoadCount;let s=[],r=0;for await(const a of e){if(!this.component)return;const{dataTransform:l}=this.component.props;l?s=l(a,s):s=s.concat(a),Object.defineProperty(s,"__diff",{enumerable:!1,value:[{startRow:r,endRow:s.length}]}),r=s.length,this._setAsyncPropValue(t,s,o)}this._onResolve(t,s)}_postProcessValue(t,e){const i=t.type;return i&&this.component&&(i.release&&i.release(t.resolvedValue,i,this.component),i.transform)?i.transform(e,i,this.component):e}_createAsyncPropData(t,e){if(!this.asyncProps[t]){const o=this.component&&this.component.props[J];this.asyncProps[t]={type:o&&o[t],lastValue:null,resolvedValue:e,pendingLoadCount:0,resolvedLoadCount:0}}}}class tl extends Qa{constructor({attributeManager:t,layer:e}){super(e),this.attributeManager=t,this.needsRedraw=!0,this.needsUpdate=!0,this.subLayers=null,this.usesPickingColorCache=!1}get layer(){return this.component}_fetch(t,e){const i=this.layer,o=i==null?void 0:i.props.fetch;return o?o(e,{propName:t,layer:i}):super._fetch(t,e)}_onResolve(t,e){const i=this.layer;if(i){const o=i.props.onDataLoad;t==="data"&&o&&o(e,{propName:t,layer:i})}}_onError(t,e){const i=this.layer;i&&i.raiseError(e,`loading ${t} of ${this.layer}`)}}const el="layer.changeFlag",il="layer.initialize",nl="layer.update",ol="layer.finalize",sl="layer.matched",Fi=2**24-1,rl=Object.freeze([]),al=bn(({oldViewport:n,viewport:t})=>n.equals(t));let D=new Uint8ClampedArray(0);const ll={data:{type:"data",value:rl,async:!0},dataComparator:{type:"function",value:null,optional:!0},_dataDiff:{type:"function",value:n=>n&&n.__diff,optional:!0},dataTransform:{type:"function",value:null,optional:!0},onDataLoad:{type:"function",value:null,optional:!0},onError:{type:"function",value:null,optional:!0},fetch:{type:"function",value:(n,{propName:t,layer:e,loaders:i,loadOptions:o,signal:s})=>{var l;const{resourceManager:r}=e.context;o=o||e.getLoadOptions(),i=i||e.props.loaders,s&&(o={...o,core:{...o==null?void 0:o.core,fetch:{...(l=o==null?void 0:o.core)==null?void 0:l.fetch,signal:s}}});let a=r.contains(n);return!a&&!o&&(r.add({resourceId:n,data:Oe(n,i),persistent:!1}),a=!0),a?r.subscribe({resourceId:n,onChange:c=>{var u;return(u=e.internalState)==null?void 0:u.reloadAsyncProp(t,c)},consumerId:e.id,requestId:t}):Oe(n,i,o)}},updateTriggers:{},visible:!0,pickable:!1,opacity:{type:"number",min:0,max:1,value:1},operation:"draw",onHover:{type:"function",value:null,optional:!0},onClick:{type:"function",value:null,optional:!0},onDragStart:{type:"function",value:null,optional:!0},onDrag:{type:"function",value:null,optional:!0},onDragEnd:{type:"function",value:null,optional:!0},coordinateSystem:"default",coordinateOrigin:{type:"array",value:[0,0,0],compare:!0},modelMatrix:{type:"array",value:null,compare:!0,optional:!0},wrapLongitude:!1,positionFormat:"XYZ",colorFormat:"RGBA",parameters:{type:"object",value:{},optional:!0,compare:2},loadOptions:{type:"object",value:null,optional:!0,ignore:!0},transitions:null,extensions:[],loaders:{type:"array",value:[],optional:!0,ignore:!0},getPolygonOffset:{type:"function",value:({layerIndex:n})=>[0,-n*100]},highlightedObjectIndex:null,autoHighlight:!1,highlightColor:{type:"accessor",value:[0,0,128,128]}};class N extends ce{constructor(){super(...arguments),this.internalState=null,this.lifecycle=rs.NO_STATE,this.parent=null}static get componentName(){return Object.prototype.hasOwnProperty.call(this,"layerName")?this.layerName:""}get root(){let t=this;for(;t.parent;)t=t.parent;return t}toString(){return`${this.constructor.layerName||this.constructor.name}({id: '${this.props.id}'})`}project(t){Z(this.internalState);const e=this.internalState.viewport||this.context.viewport,i=Je(t,{viewport:e,modelMatrix:this.props.modelMatrix,coordinateOrigin:this.props.coordinateOrigin,coordinateSystem:this.props.coordinateSystem}),[o,s,r]=as(i,e.pixelProjectionMatrix);return t.length===2?[o,s]:[o,s,r]}unproject(t){return Z(this.internalState),(this.internalState.viewport||this.context.viewport).unproject(t)}projectPosition(t,e){Z(this.internalState);const i=this.internalState.viewport||this.context.viewport;return or(t,{viewport:i,modelMatrix:this.props.modelMatrix,coordinateOrigin:this.props.coordinateOrigin,coordinateSystem:this.props.coordinateSystem,...e})}get isComposite(){return!1}get isDrawable(){return!0}setState(t){this.setChangeFlags({stateChanged:!0}),Object.assign(this.state,t),this.setNeedsRedraw()}setNeedsRedraw(){this.internalState&&(this.internalState.needsRedraw=!0)}setNeedsUpdate(){this.internalState&&(this.context.layerManager.setNeedsUpdate(String(this)),this.internalState.needsUpdate=!0)}get isLoaded(){return this.internalState?!this.internalState.isAsyncPropLoading():!1}get wrapLongitude(){return this.props.wrapLongitude}isPickable(){return this.props.pickable&&this.props.visible}getModels(){const t=this.state;return t&&(t.models||t.model&&[t.model])||[]}setShaderModuleProps(...t){for(const e of this.getModels())e.shaderInputs.setProps(...t)}getAttributeManager(){return this.internalState&&this.internalState.attributeManager}getCurrentLayer(){return this.internalState&&this.internalState.layer}getLoadOptions(){return this.props.loadOptions}use64bitPositions(){const{coordinateSystem:t}=this.props;return t==="default"||t==="lnglat"||t==="cartesian"}onHover(t,e){return this.props.onHover&&this.props.onHover(t,e)||!1}onClick(t,e){return this.props.onClick&&this.props.onClick(t,e)||!1}nullPickingColor(){return[0,0,0]}encodePickingColor(t,e=[]){return e[0]=t+1&255,e[1]=t+1>>8&255,e[2]=t+1>>8>>8&255,e}decodePickingColor(t){Z(t instanceof Uint8Array);const[e,i,o]=t;return e+i*256+o*65536-1}getNumInstances(){return Number.isFinite(this.props.numInstances)?this.props.numInstances:this.state&&this.state.numInstances!==void 0?this.state.numInstances:za(this.props.data)}getStartIndices(){return this.props.startIndices?this.props.startIndices:this.state&&this.state.startIndices?this.state.startIndices:null}getBounds(){var t;return(t=this.getAttributeManager())==null?void 0:t.getBounds(["positions","instancePositions"])}getShaders(t){t=zi(t,{disableWarnings:!0,modules:this.context.defaultShaderModules});for(const e of this.props.extensions)t=zi(t,e.getShaders.call(this,e));return t}shouldUpdateState(t){return t.changeFlags.propsOrDataChanged}updateState(t){const e=this.getAttributeManager(),{dataChanged:i}=t.changeFlags;if(i&&e)if(Array.isArray(i))for(const o of i)e.invalidateAll(o);else e.invalidateAll();if(e){const{props:o}=t,s=this.internalState.hasPickingBuffer,r=Number.isInteger(o.highlightedObjectIndex)||!!o.pickable||o.extensions.some(a=>a.getNeedsPickingBuffer.call(this,a));if(s!==r){this.internalState.hasPickingBuffer=r;const{pickingColors:a,instancePickingColors:l}=e.attributes,c=a||l;c&&(r&&c.constant&&(c.constant=!1,e.invalidate(c.id)),!c.value&&!r&&(c.constant=!0,c.value=[0,0,0]))}}}finalizeState(t){for(const i of this.getModels())i.destroy();const e=this.getAttributeManager();e&&e.finalize(),this.context&&this.context.resourceManager.unsubscribe({consumerId:this.id}),this.internalState&&(this.internalState.uniformTransitions.clear(),this.internalState.finalize())}draw(t){for(const e of this.getModels())e.draw(t.renderPass)}getPickingInfo({info:t,mode:e,sourceLayer:i}){const{index:o}=t;return o>=0&&Array.isArray(this.props.data)&&(t.object=this.props.data[o]),t}raiseError(t,e){var i,o,s,r;e&&(t=new Error(`${e}: ${t.message}`,{cause:t})),(o=(i=this.props).onError)!=null&&o.call(i,t)||(r=(s=this.context)==null?void 0:s.onError)==null||r.call(s,t,this)}getNeedsRedraw(t={clearRedrawFlags:!1}){return this._getNeedsRedraw(t)}needsUpdate(){return this.internalState?this.internalState.needsUpdate||this.hasUniformTransition()||this.shouldUpdateState(this._getUpdateParams()):!1}hasUniformTransition(){var t;return((t=this.internalState)==null?void 0:t.uniformTransitions.active)||!1}activateViewport(t){if(!this.internalState)return;const e=this.internalState.viewport;this.internalState.viewport=t,(!e||!al({oldViewport:e,viewport:t}))&&(this.setChangeFlags({viewportChanged:!0}),this.isComposite?this.needsUpdate()&&this.setNeedsUpdate():this._update())}invalidateAttribute(t="all"){const e=this.getAttributeManager();e&&(t==="all"?e.invalidateAll():e.invalidate(t))}updateAttributes(t){let e=!1;for(const i in t)t[i].layoutChanged()&&(e=!0);for(const i of this.getModels())this._setModelAttributes(i,t,e)}_updateAttributes(){const t=this.getAttributeManager();if(!t)return;const e=this.props,i=this.getNumInstances(),o=this.getStartIndices();t.update({data:e.data,numInstances:i,startIndices:o,props:e,transitions:e.transitions,buffers:e.data.attributes,context:this});const s=t.getChangedAttributes({clearChangedFlags:!0});this.updateAttributes(s)}_updateAttributeTransition(){const t=this.getAttributeManager();t&&t.updateTransition()}_updateUniformTransition(){const{uniformTransitions:t}=this.internalState;if(t.active){const e=t.update(),i=Object.create(this.props);for(const o in e)Object.defineProperty(i,o,{value:e[o]});return i}return this.props}calculateInstancePickingColors(t,{numInstances:e}){if(t.constant)return;const i=Math.floor(D.length/4);if(this.internalState.usesPickingColorCache=!0,i<e){e>Fi&&T.warn("Layer has too many data objects. Picking might not be able to distinguish all objects.")(),D=Ht.allocate(D,e,{size:4,copy:!0,maxCount:Math.max(e,Fi)});const o=Math.floor(D.length/4),s=[0,0,0];for(let r=i;r<o;r++)this.encodePickingColor(r,s),D[r*4+0]=s[0],D[r*4+1]=s[1],D[r*4+2]=s[2],D[r*4+3]=0}t.value=D.subarray(0,e*4)}_setModelAttributes(t,e,i=!1){var a;if(!Object.keys(e).length)return;if(i){const l=this.getAttributeManager();t.setBufferLayout(l.getBufferLayouts(t)),e=l.getAttributes()}const o=((a=t.userData)==null?void 0:a.excludeAttributes)||{},s={},r={};for(const l in e){if(o[l])continue;const c=e[l].getValue();for(const u in c){const f=c[u];f instanceof R?e[l].settings.isIndexed?t.setIndexBuffer(f):s[u]=f:f&&(r[u]=f)}}t.setAttributes(s),t.setConstantAttributes(r)}disablePickingIndex(t){const e=this.props.data;if(!("attributes"in e)){this._disablePickingIndex(t);return}const{pickingColors:i,instancePickingColors:o}=this.getAttributeManager().attributes,s=i||o,r=s&&e.attributes&&e.attributes[s.id];if(r&&r.value){const a=r.value,l=this.encodePickingColor(t);for(let c=0;c<e.length;c++){const u=s.getVertexOffset(c);a[u]===l[0]&&a[u+1]===l[1]&&a[u+2]===l[2]&&this._disablePickingIndex(c)}}else this._disablePickingIndex(t)}_disablePickingIndex(t){const{pickingColors:e,instancePickingColors:i}=this.getAttributeManager().attributes,o=e||i;if(!o)return;const s=o.getVertexOffset(t),r=o.getVertexOffset(t+1);o.buffer.write(new Uint8Array(r-s),s)}restorePickingColors(){const{pickingColors:t,instancePickingColors:e}=this.getAttributeManager().attributes,i=t||e;i&&(this.internalState.usesPickingColorCache&&i.value.buffer!==D.buffer&&(i.value=D.subarray(0,i.value.length)),i.updateSubBuffer({startOffset:0}))}_initialize(){Z(!this.internalState),B(il,this);const t=this._getAttributeManager();t&&t.addInstanced({instancePickingColors:{type:"uint8",size:4,noAlloc:!0,update:this.calculateInstancePickingColors}}),this.internalState=new tl({attributeManager:t,layer:this}),this._clearChangeFlags(),this.state={},Object.defineProperty(this.state,"attributeManager",{get:()=>(T.deprecated("layer.state.attributeManager","layer.getAttributeManager()")(),t)}),this.internalState.uniformTransitions=new wa(this.context.timeline),this.internalState.onAsyncPropUpdated=this._onAsyncPropUpdated.bind(this),this.internalState.setAsyncProps(this.props),this.initializeState(this.context);for(const e of this.props.extensions)e.initializeState.call(this,this.context,e);this.setChangeFlags({dataChanged:"init",propsChanged:"init",viewportChanged:!0,extensionsChanged:!0}),this._update()}_transferState(t){B(sl,this,this===t);const{state:e,internalState:i}=t;this!==t&&(this.internalState=i,this.state=e,this.internalState.setAsyncProps(this.props),this._diffProps(this.props,this.internalState.getOldProps()))}_update(){const t=this.needsUpdate();if(B(nl,this,t),!t)return;this.context.stats.get("Layer updates").incrementCount();const e=this.props,i=this.context,o=this.internalState,s=i.viewport,r=this._updateUniformTransition();o.propsInTransition=r,i.viewport=o.viewport||s,this.props=r;try{const a=this._getUpdateParams(),l=this.getModels();if(i.device)this.updateState(a);else try{this.updateState(a)}catch{}for(const u of this.props.extensions)u.updateState.call(this,a,u);this.setNeedsRedraw(),this._updateAttributes();const c=this.getModels()[0]!==l[0];this._postUpdate(a,c)}finally{i.viewport=s,this.props=e,this._clearChangeFlags(),o.needsUpdate=!1,o.resetOldProps()}}_finalize(){B(ol,this),this.finalizeState(this.context);for(const t of this.props.extensions)t.finalizeState.call(this,this.context,t)}_drawLayer({renderPass:t,shaderModuleProps:e=null,uniforms:i={},parameters:o={}}){this._updateAttributeTransition();const s=this.props,r=this.context;this.props=this.internalState.propsInTransition||s;try{e&&this.setShaderModuleProps(e);const{getPolygonOffset:a}=this.props,l=a&&a(i)||[0,0];r.device instanceof me&&r.device.setParametersWebGL({polygonOffset:l});const c=r.device instanceof me?null:cl(o);if(ul(this.getModels(),t,o,c),r.device instanceof me)r.device.withParametersWebGL(o,()=>{const u={renderPass:t,shaderModuleProps:e,uniforms:i,parameters:o,context:r};for(const f of this.props.extensions)f.draw.call(this,u,f);this.draw(u)});else{c!=null&&c.renderPassParameters&&t.setParameters(c.renderPassParameters);const u={renderPass:t,shaderModuleProps:e,uniforms:i,parameters:o,context:r};for(const f of this.props.extensions)f.draw.call(this,u,f);this.draw(u)}}finally{this.props=s}}getChangeFlags(){var t;return(t=this.internalState)==null?void 0:t.changeFlags}setChangeFlags(t){if(!this.internalState)return;const{changeFlags:e}=this.internalState;for(const o in t)if(t[o]){let s=!1;switch(o){case"dataChanged":const r=t[o],a=e[o];r&&Array.isArray(a)&&(e.dataChanged=Array.isArray(r)?a.concat(r):r,s=!0);default:e[o]||(e[o]=t[o],s=!0)}s&&B(el,this,o,t)}const i=!!(e.dataChanged||e.updateTriggersChanged||e.propsChanged||e.extensionsChanged);e.propsOrDataChanged=i,e.somethingChanged=i||e.viewportChanged||e.stateChanged}_clearChangeFlags(){this.internalState.changeFlags={dataChanged:!1,propsChanged:!1,updateTriggersChanged:!1,viewportChanged:!1,stateChanged:!1,extensionsChanged:!1,propsOrDataChanged:!1,somethingChanged:!1}}_diffProps(t,e){var o;const i=Sa(t,e);if(i.updateTriggersChanged)for(const s in i.updateTriggersChanged)i.updateTriggersChanged[s]&&this.invalidateAttribute(s);if(i.transitionsChanged)for(const s in i.transitionsChanged)this.internalState.uniformTransitions.add(s,e[s],t[s],(o=t.transitions)==null?void 0:o[s]);return this.setChangeFlags(i)}validateProps(){Aa(this.props)}updateAutoHighlight(t){this.props.autoHighlight&&!Number.isInteger(this.props.highlightedObjectIndex)&&this._updateAutoHighlight(t)}_updateAutoHighlight(t){const e={highlightedObjectColor:t.picked?t.color:null},{highlightColor:i}=this.props;t.picked&&typeof i=="function"&&(e.highlightColor=i(t)),this.setShaderModuleProps({picking:e}),this.setNeedsRedraw()}_getAttributeManager(){const t=this.context;return new xa(t.device,{id:this.props.id,stats:t.stats,timeline:t.timeline})}_postUpdate(t,e){const{props:i,oldProps:o}=t,s=this.state.model;s!=null&&s.isInstanced&&s.setInstanceCount(this.getNumInstances());const{autoHighlight:r,highlightedObjectIndex:a,highlightColor:l}=i;if(e||o.autoHighlight!==r||o.highlightedObjectIndex!==a||o.highlightColor!==l){const c={};Array.isArray(l)&&(c.highlightColor=l),(e||o.autoHighlight!==r||a!==o.highlightedObjectIndex)&&(c.highlightedObjectColor=Number.isFinite(a)&&a>=0?this.encodePickingColor(a):null),this.setShaderModuleProps({picking:c})}}_getUpdateParams(){return{props:this.props,oldProps:this.internalState.getOldProps(),context:this.context,changeFlags:this.internalState.changeFlags}}_getNeedsRedraw(t){if(!this.internalState)return!1;let e=!1;e=e||this.internalState.needsRedraw&&this.id;const i=this.getAttributeManager(),o=i?i.getNeedsRedraw(t):!1;if(e=e||o,e)for(const s of this.props.extensions)s.onNeedsRedraw.call(this,s);return this.internalState.needsRedraw=this.internalState.needsRedraw&&!t.clearRedrawFlags,e}_onAsyncPropUpdated(){this._diffProps(this.props,this.internalState.getOldProps()),this.setNeedsUpdate()}}N.defaultProps=ll;N.layerName="Layer";function cl(n){const{blendConstant:t,...e}=n;return t?{pipelineParameters:e,renderPassParameters:{blendConstant:t}}:{pipelineParameters:e}}function ul(n,t,e,i){for(const o of n)o.device.type==="webgpu"?(fl(o,t),o.setParameters({...o.parameters,...i==null?void 0:i.pipelineParameters})):o.setParameters(e)}function fl(n,t){var r,a;const e=t.props.framebuffer||(t.framebuffer??null);if(!e)return;const i=e.colorAttachments.map(l=>{var c;return((c=l==null?void 0:l.texture)==null?void 0:c.format)??null}),o=(a=(r=e.depthStencilAttachment)==null?void 0:r.texture)==null?void 0:a.format,s=n;(!dl(s.props.colorAttachmentFormats,i)||s.props.depthStencilAttachmentFormat!==o)&&(s.props.colorAttachmentFormats=i,s.props.depthStencilAttachmentFormat=o,s._setPipelineNeedsUpdate("attachment formats"))}function dl(n,t){if(n===t)return!0;if(!n||!t||n.length!==t.length)return!1;for(let e=0;e<n.length;e++)if(n[e]!==t[e])return!1;return!0}const hl="compositeLayer.renderLayers";class ue extends N{get isComposite(){return!0}get isDrawable(){return!1}get isLoaded(){return super.isLoaded&&this.getSubLayers().every(t=>t.isLoaded)}getSubLayers(){return this.internalState&&this.internalState.subLayers||[]}initializeState(t){}setState(t){super.setState(t),this.setNeedsUpdate()}getPickingInfo({info:t}){const{object:e}=t;return e&&e.__source&&e.__source.parent&&e.__source.parent.id===this.id&&(t.object=e.__source.object,t.index=e.__source.index),t}filterSubLayer(t){return!0}shouldRenderSubLayer(t,e){return e&&e.length}getSubLayerClass(t,e){const{_subLayerProps:i}=this.props;return i&&i[t]&&i[t].type||e}getSubLayerRow(t,e,i){return t.__source={parent:this,object:e,index:i},t}getSubLayerAccessor(t){if(typeof t=="function"){const e={index:-1,data:this.props.data,target:[]};return(i,o)=>i&&i.__source?(e.index=i.__source.index,t(i.__source.object,e)):t(i,o)}return t}getSubLayerProps(t={}){var I;const{opacity:e,pickable:i,visible:o,parameters:s,getPolygonOffset:r,highlightedObjectIndex:a,autoHighlight:l,highlightColor:c,coordinateSystem:u,coordinateOrigin:f,wrapLongitude:d,positionFormat:h,modelMatrix:p,extensions:g,fetch:m,operation:x,_subLayerProps:b}=this.props,v={id:"",updateTriggers:{},opacity:e,pickable:i,visible:o,parameters:s,getPolygonOffset:r,highlightedObjectIndex:a,autoHighlight:l,highlightColor:c,coordinateSystem:u,coordinateOrigin:f,wrapLongitude:d,positionFormat:h,modelMatrix:p,extensions:g,fetch:m,operation:x},_=b&&t.id&&b[t.id],C=_&&_.updateTriggers,w=t.id||"sublayer";if(_){const O=this.props[J],L=t.type?t.type._propTypes:{};for(const E in _){const F=L[E]||O[E];F&&F.type==="accessor"&&(_[E]=this.getSubLayerAccessor(_[E]))}}Object.assign(v,t,_),v.id=`${this.props.id}-${w}`,v.updateTriggers={all:(I=this.props.updateTriggers)==null?void 0:I.all,...t.updateTriggers,...C};for(const O of g){const L=O.getSubLayerProps.call(this,O);L&&Object.assign(v,L,{updateTriggers:Object.assign(v.updateTriggers,L.updateTriggers)})}return v}_updateAutoHighlight(t){for(const e of this.getSubLayers())e.updateAutoHighlight(t)}_getAttributeManager(){return null}_postUpdate(t,e){let i=this.internalState.subLayers;const o=!i||this.needsUpdate();if(o){const s=this.renderLayers();i=ls(s,Boolean),this.internalState.subLayers=i}B(hl,this,o,i);for(const s of i)s.parent=this}}ue.layerName="CompositeLayer";class no{constructor(t){this.indexStarts=[0],this.vertexStarts=[0],this.vertexCount=0,this.instanceCount=0;const{attributes:e={}}=t;this.typedArrayManager=Ht,this.attributes={},this._attributeDefs=e,this.opts=t,this.updateGeometry(t)}updateGeometry(t){Object.assign(this.opts,t);const{data:e,buffers:i={},getGeometry:o,geometryBuffer:s,positionFormat:r,dataChanged:a,normalize:l=!0}=this.opts;if(this.data=e,this.getGeometry=o,this.positionSize=s&&s.size||(r==="XY"?2:3),this.buffers=i,this.normalize=l,s&&(Z(e.startIndices),this.getGeometry=this.getGeometryFromBuffer(s),l||(i.vertexPositions=s)),this.geometryBuffer=i.vertexPositions,Array.isArray(a))for(const c of a)this._rebuildGeometry(c);else this._rebuildGeometry()}updatePartialGeometry({startRow:t,endRow:e}){this._rebuildGeometry({startRow:t,endRow:e})}getGeometryFromBuffer(t){const e=t.value||t;return ArrayBuffer.isView(e)?Wn(e,{size:this.positionSize,offset:t.offset,stride:t.stride,startIndices:this.data.startIndices}):null}_allocate(t,e){const{attributes:i,buffers:o,_attributeDefs:s,typedArrayManager:r}=this;for(const a in s)if(a in o)r.release(i[a]),i[a]=null;else{const l=s[a];l.copy=e,i[a]=r.allocate(i[a],t,l)}}_forEachGeometry(t,e,i){const{data:o,getGeometry:s}=this,{iterable:r,objectInfo:a}=ct(o,e,i);for(const l of r){a.index++;const c=s?s(l,a):null;t(c,a.index)}}_rebuildGeometry(t){if(!this.data)return;let{indexStarts:e,vertexStarts:i,instanceCount:o}=this;const{data:s,geometryBuffer:r}=this,{startRow:a=0,endRow:l=1/0}=t||{},c={};if(t||(e=[0],i=[0]),this.normalize||!r)this._forEachGeometry((f,d)=>{const h=f&&this.normalizeGeometry(f);c[d]=h,i[d+1]=i[d]+(h?this.getGeometrySize(h):0)},a,l),o=i[i.length-1];else if(i=s.startIndices,o=i[s.length]||0,ArrayBuffer.isView(r))o=o||r.length/this.positionSize;else if(r instanceof R){const f=this.positionSize*4;o=o||r.byteLength/f}else if(r.buffer){const f=r.stride||this.positionSize*4;o=o||r.buffer.byteLength/f}else if(r.value){const f=r.value,d=r.stride/f.BYTES_PER_ELEMENT||this.positionSize;o=o||f.length/d}this._allocate(o,!!t),this.indexStarts=e,this.vertexStarts=i,this.instanceCount=o;const u={};this._forEachGeometry((f,d)=>{const h=c[d]||f;u.vertexStart=i[d],u.indexStart=e[d];const p=d<i.length-1?i[d+1]:o;u.geometrySize=p-i[d],u.geometryIndex=d,this.updateGeometryAttributes(h,u)},a,l),this.vertexCount=e[e.length-1]}}const ki=`layout(std140) uniform arcUniforms {
  bool greatCircle;
  bool useShortestPath;
  float numSegments;
  float widthScale;
  float widthMinPixels;
  float widthMaxPixels;
  highp int widthUnits;
} arc;
`,pl={name:"arc",vs:ki,fs:ki,uniformTypes:{greatCircle:"f32",useShortestPath:"f32",numSegments:"f32",widthScale:"f32",widthMinPixels:"f32",widthMaxPixels:"f32",widthUnits:"i32"}},gl=`#version 300 es
#define SHADER_NAME arc-layer-vertex-shader
in vec4 instanceSourceColors;
in vec4 instanceTargetColors;
in vec3 instanceSourcePositions;
in vec3 instanceSourcePositions64Low;
in vec3 instanceTargetPositions;
in vec3 instanceTargetPositions64Low;
in vec3 instancePickingColors;
in float instanceWidths;
in float instanceHeights;
in float instanceTilts;
out vec4 vColor;
out vec2 uv;
out float isValid;
float paraboloid(float distance, float sourceZ, float targetZ, float ratio) {
float deltaZ = targetZ - sourceZ;
float dh = distance * instanceHeights;
if (dh == 0.0) {
return sourceZ + deltaZ * ratio;
}
float unitZ = deltaZ / dh;
float p2 = unitZ * unitZ + 1.0;
float dir = step(deltaZ, 0.0);
float z0 = mix(sourceZ, targetZ, dir);
float r = mix(ratio, 1.0 - ratio, dir);
return sqrt(r * (p2 - r)) * dh + z0;
}
vec2 getExtrusionOffset(vec2 line_clipspace, float offset_direction, float width) {
vec2 dir_screenspace = normalize(line_clipspace * project.viewportSize);
dir_screenspace = vec2(-dir_screenspace.y, dir_screenspace.x);
return dir_screenspace * offset_direction * width / 2.0;
}
float getSegmentRatio(float index) {
return smoothstep(0.0, 1.0, index / (arc.numSegments - 1.0));
}
vec3 interpolateFlat(vec3 source, vec3 target, float segmentRatio) {
float distance = length(source.xy - target.xy);
float z = paraboloid(distance, source.z, target.z, segmentRatio);
float tiltAngle = radians(instanceTilts);
vec2 tiltDirection = normalize(target.xy - source.xy);
vec2 tilt = vec2(-tiltDirection.y, tiltDirection.x) * z * sin(tiltAngle);
return vec3(
mix(source.xy, target.xy, segmentRatio) + tilt,
z * cos(tiltAngle)
);
}
float getAngularDist (vec2 source, vec2 target) {
vec2 sourceRadians = radians(source);
vec2 targetRadians = radians(target);
vec2 sin_half_delta = sin((sourceRadians - targetRadians) / 2.0);
vec2 shd_sq = sin_half_delta * sin_half_delta;
float a = shd_sq.y + cos(sourceRadians.y) * cos(targetRadians.y) * shd_sq.x;
return 2.0 * asin(sqrt(a));
}
vec3 interpolateGreatCircle(vec3 source, vec3 target, vec3 source3D, vec3 target3D, float angularDist, float t) {
vec2 lngLat;
if(abs(angularDist - PI) < 0.001) {
lngLat = (1.0 - t) * source.xy + t * target.xy;
} else {
float a = sin((1.0 - t) * angularDist);
float b = sin(t * angularDist);
vec3 p = source3D.yxz * a + target3D.yxz * b;
lngLat = degrees(vec2(atan(p.y, -p.x), atan(p.z, length(p.xy))));
}
float z = paraboloid(angularDist * EARTH_RADIUS, source.z, target.z, t);
return vec3(lngLat, z);
}
void main(void) {
geometry.worldPosition = instanceSourcePositions;
geometry.worldPositionAlt = instanceTargetPositions;
float segmentIndex = float(gl_VertexID / 2);
float segmentSide = mod(float(gl_VertexID), 2.) == 0. ? -1. : 1.;
float segmentRatio = getSegmentRatio(segmentIndex);
float prevSegmentRatio = getSegmentRatio(max(0.0, segmentIndex - 1.0));
float nextSegmentRatio = getSegmentRatio(min(arc.numSegments - 1.0, segmentIndex + 1.0));
float indexDir = mix(-1.0, 1.0, step(segmentIndex, 0.0));
isValid = 1.0;
uv = vec2(segmentRatio, segmentSide);
geometry.uv = uv;
geometry.pickingColor = instancePickingColors;
vec4 curr;
vec4 next;
vec3 source;
vec3 target;
if ((arc.greatCircle || project.projectionMode == PROJECTION_MODE_GLOBE) && project.coordinateSystem == COORDINATE_SYSTEM_LNGLAT) {
source = project_globe_(vec3(instanceSourcePositions.xy, 0.0));
target = project_globe_(vec3(instanceTargetPositions.xy, 0.0));
float angularDist = getAngularDist(instanceSourcePositions.xy, instanceTargetPositions.xy);
vec3 prevPos = interpolateGreatCircle(instanceSourcePositions, instanceTargetPositions, source, target, angularDist, prevSegmentRatio);
vec3 currPos = interpolateGreatCircle(instanceSourcePositions, instanceTargetPositions, source, target, angularDist, segmentRatio);
vec3 nextPos = interpolateGreatCircle(instanceSourcePositions, instanceTargetPositions, source, target, angularDist, nextSegmentRatio);
if (abs(currPos.x - prevPos.x) > 180.0) {
indexDir = -1.0;
isValid = 0.0;
} else if (abs(currPos.x - nextPos.x) > 180.0) {
indexDir = 1.0;
isValid = 0.0;
}
nextPos = indexDir < 0.0 ? prevPos : nextPos;
nextSegmentRatio = indexDir < 0.0 ? prevSegmentRatio : nextSegmentRatio;
if (isValid == 0.0) {
nextPos.x += nextPos.x > 0.0 ? -360.0 : 360.0;
float t = ((currPos.x > 0.0 ? 180.0 : -180.0) - currPos.x) / (nextPos.x - currPos.x);
currPos = mix(currPos, nextPos, t);
segmentRatio = mix(segmentRatio, nextSegmentRatio, t);
}
vec3 currPos64Low = mix(instanceSourcePositions64Low, instanceTargetPositions64Low, segmentRatio);
vec3 nextPos64Low = mix(instanceSourcePositions64Low, instanceTargetPositions64Low, nextSegmentRatio);
curr = project_position_to_clipspace(currPos, currPos64Low, vec3(0.0), geometry.position);
next = project_position_to_clipspace(nextPos, nextPos64Low, vec3(0.0));
} else {
vec3 source_world = instanceSourcePositions;
vec3 target_world = instanceTargetPositions;
if (arc.useShortestPath) {
source_world.x = mod(source_world.x + 180., 360.0) - 180.;
target_world.x = mod(target_world.x + 180., 360.0) - 180.;
float deltaLng = target_world.x - source_world.x;
if (deltaLng > 180.) target_world.x -= 360.;
if (deltaLng < -180.) source_world.x -= 360.;
}
source = project_position(source_world, instanceSourcePositions64Low);
target = project_position(target_world, instanceTargetPositions64Low);
float antiMeridianX = 0.0;
if (arc.useShortestPath) {
if (project.projectionMode == PROJECTION_MODE_WEB_MERCATOR_AUTO_OFFSET) {
antiMeridianX = -(project.coordinateOrigin.x + 180.) / 360. * TILE_SIZE;
}
float thresholdRatio = (antiMeridianX - source.x) / (target.x - source.x);
if (prevSegmentRatio <= thresholdRatio && nextSegmentRatio > thresholdRatio) {
isValid = 0.0;
indexDir = sign(segmentRatio - thresholdRatio);
segmentRatio = thresholdRatio;
}
}
nextSegmentRatio = indexDir < 0.0 ? prevSegmentRatio : nextSegmentRatio;
vec3 currPos = interpolateFlat(source, target, segmentRatio);
vec3 nextPos = interpolateFlat(source, target, nextSegmentRatio);
if (arc.useShortestPath) {
if (nextPos.x < antiMeridianX) {
currPos.x += TILE_SIZE;
nextPos.x += TILE_SIZE;
}
}
curr = project_common_position_to_clipspace(vec4(currPos, 1.0));
next = project_common_position_to_clipspace(vec4(nextPos, 1.0));
geometry.position = vec4(currPos, 1.0);
}
float widthPixels = clamp(
project_size_to_pixel(instanceWidths * arc.widthScale, arc.widthUnits),
arc.widthMinPixels, arc.widthMaxPixels
);
vec3 offset = vec3(
getExtrusionOffset((next.xy - curr.xy) * indexDir, segmentSide, widthPixels),
0.0);
DECKGL_FILTER_SIZE(offset, geometry);
DECKGL_FILTER_GL_POSITION(curr, geometry);
gl_Position = curr + vec4(project_pixel_size_to_clipspace(offset.xy), 0.0, 0.0);
vec4 color = mix(instanceSourceColors, instanceTargetColors, segmentRatio);
vColor = vec4(color.rgb, color.a * layer.opacity);
DECKGL_FILTER_COLOR(vColor, geometry);
}
`,ml=`#version 300 es
#define SHADER_NAME arc-layer-fragment-shader
precision highp float;
in vec4 vColor;
in vec2 uv;
in float isValid;
out vec4 fragColor;
void main(void) {
if (isValid == 0.0) {
discard;
}
fragColor = vColor;
geometry.uv = uv;
DECKGL_FILTER_COLOR(fragColor, geometry);
}
`,Xt=[0,0,0,255],yl={getSourcePosition:{type:"accessor",value:n=>n.sourcePosition},getTargetPosition:{type:"accessor",value:n=>n.targetPosition},getSourceColor:{type:"accessor",value:Xt},getTargetColor:{type:"accessor",value:Xt},getWidth:{type:"accessor",value:1},getHeight:{type:"accessor",value:1},getTilt:{type:"accessor",value:0},greatCircle:!1,numSegments:{type:"number",value:50,min:1},widthUnits:"pixels",widthScale:{type:"number",value:1,min:0},widthMinPixels:{type:"number",value:0,min:0},widthMaxPixels:{type:"number",value:Number.MAX_SAFE_INTEGER,min:0}};class oo extends N{getBounds(){var t;return(t=this.getAttributeManager())==null?void 0:t.getBounds(["instanceSourcePositions","instanceTargetPositions"])}getShaders(){return super.getShaders({vs:gl,fs:ml,modules:[V,W,pl]})}get wrapLongitude(){return!1}initializeState(){this.getAttributeManager().addInstanced({instanceSourcePositions:{size:3,type:"float64",fp64:this.use64bitPositions(),transition:!0,accessor:"getSourcePosition"},instanceTargetPositions:{size:3,type:"float64",fp64:this.use64bitPositions(),transition:!0,accessor:"getTargetPosition"},instanceSourceColors:{size:this.props.colorFormat.length,type:"unorm8",transition:!0,accessor:"getSourceColor",defaultValue:Xt},instanceTargetColors:{size:this.props.colorFormat.length,type:"unorm8",transition:!0,accessor:"getTargetColor",defaultValue:Xt},instanceWidths:{size:1,transition:!0,accessor:"getWidth",defaultValue:1},instanceHeights:{size:1,transition:!0,accessor:"getHeight",defaultValue:1},instanceTilts:{size:1,transition:!0,accessor:"getTilt",defaultValue:0}})}updateState(t){var e;super.updateState(t),t.changeFlags.extensionsChanged&&((e=this.state.model)==null||e.destroy(),this.state.model=this._getModel(),this.getAttributeManager().invalidateAll())}draw({uniforms:t}){const{widthUnits:e,widthScale:i,widthMinPixels:o,widthMaxPixels:s,greatCircle:r,wrapLongitude:a,numSegments:l}=this.props,c={numSegments:l,widthUnits:G[e],widthScale:i,widthMinPixels:o,widthMaxPixels:s,greatCircle:r,useShortestPath:a},u=this.state.model;u.shaderInputs.setProps({arc:c}),u.setVertexCount(l*2),u.draw(this.context.renderPass)}_getModel(){return new z(this.context.device,{...this.getShaders(),id:this.props.id,bufferLayout:this.getAttributeManager().getBufferLayouts(),topology:"triangle-strip",isInstanced:!0})}}oo.layerName="ArcLayer";oo.defaultProps=yl;const vl=new Uint32Array([0,2,1,0,3,2]),_l=new Float32Array([0,1,0,0,1,0,1,1]);function xl(n,t){if(!t)return bl(n);const e=Math.max(Math.abs(n[0][0]-n[3][0]),Math.abs(n[1][0]-n[2][0])),i=Math.max(Math.abs(n[1][1]-n[0][1]),Math.abs(n[2][1]-n[3][1])),o=Math.ceil(e/t)+1,s=Math.ceil(i/t)+1,r=(o-1)*(s-1)*6,a=new Uint32Array(r),l=new Float32Array(o*s*2),c=new Float64Array(o*s*3);let u=0,f=0;for(let d=0;d<o;d++){const h=d/(o-1);for(let p=0;p<s;p++){const g=p/(s-1),m=Pl(n,h,g);c[u*3+0]=m[0],c[u*3+1]=m[1],c[u*3+2]=m[2]||0,l[u*2+0]=h,l[u*2+1]=1-g,d>0&&p>0&&(a[f++]=u-s,a[f++]=u-s-1,a[f++]=u-1,a[f++]=u-s,a[f++]=u-1,a[f++]=u),u++}}return{vertexCount:r,positions:c,indices:a,texCoords:l}}function bl(n){const t=new Float64Array(12);for(let e=0;e<n.length;e++)t[e*3+0]=n[e][0],t[e*3+1]=n[e][1],t[e*3+2]=n[e][2]||0;return{vertexCount:6,positions:t,indices:vl,texCoords:_l}}function Pl(n,t,e){return Ut(Ut(n[0],n[1],e),Ut(n[3],n[2],e),t)}const Bi=`layout(std140) uniform bitmapUniforms {
  vec4 bounds;
  float coordinateConversion;
  float desaturate;
  vec3 tintColor;
  vec4 transparentColor;
} bitmap;
`,Cl={name:"bitmap",vs:Bi,fs:Bi,uniformTypes:{bounds:"vec4<f32>",coordinateConversion:"f32",desaturate:"f32",tintColor:"vec3<f32>",transparentColor:"vec4<f32>"}},Ll=`#version 300 es
#define SHADER_NAME bitmap-layer-vertex-shader

in vec2 texCoords;
in vec3 positions;
in vec3 positions64Low;

out vec2 vTexCoord;
out vec2 vTexPos;

const vec3 pickingColor = vec3(1.0, 0.0, 0.0);

void main(void) {
  geometry.worldPosition = positions;
  geometry.uv = texCoords;
  geometry.pickingColor = pickingColor;

  gl_Position = project_position_to_clipspace(positions, positions64Low, vec3(0.0), geometry.position);
  DECKGL_FILTER_GL_POSITION(gl_Position, geometry);

  vTexCoord = texCoords;

  if (bitmap.coordinateConversion < -0.5) {
    vTexPos = geometry.position.xy + project.commonOrigin.xy;
  } else if (bitmap.coordinateConversion > 0.5) {
    vTexPos = geometry.worldPosition.xy;
  }

  vec4 color = vec4(0.0);
  DECKGL_FILTER_COLOR(color, geometry);
}
`,wl=`
vec3 packUVsIntoRGB(vec2 uv) {
  // Extract the top 8 bits. We want values to be truncated down so we can add a fraction
  vec2 uv8bit = floor(uv * 256.);

  // Calculate the normalized remainders of u and v parts that do not fit into 8 bits
  // Scale and clamp to 0-1 range
  vec2 uvFraction = fract(uv * 256.);
  vec2 uvFraction4bit = floor(uvFraction * 16.);

  // Remainder can be encoded in blue channel, encode as 4 bits for pixel coordinates
  float fractions = uvFraction4bit.x + uvFraction4bit.y * 16.;

  return vec3(uv8bit, fractions) / 255.;
}
`,Al=`#version 300 es
#define SHADER_NAME bitmap-layer-fragment-shader

#ifdef GL_ES
precision highp float;
#endif

uniform sampler2D bitmapTexture;

in vec2 vTexCoord;
in vec2 vTexPos;

out vec4 fragColor;

/* projection utils */
const float TILE_SIZE = 512.0;
const float PI = 3.1415926536;
const float WORLD_SCALE = TILE_SIZE / PI / 2.0;

// from degrees to Web Mercator
vec2 lnglat_to_mercator(vec2 lnglat) {
  float x = lnglat.x;
  float y = clamp(lnglat.y, -89.9, 89.9);
  return vec2(
    radians(x) + PI,
    PI + log(tan(PI * 0.25 + radians(y) * 0.5))
  ) * WORLD_SCALE;
}

// from Web Mercator to degrees
vec2 mercator_to_lnglat(vec2 xy) {
  xy /= WORLD_SCALE;
  return degrees(vec2(
    xy.x - PI,
    atan(exp(xy.y - PI)) * 2.0 - PI * 0.5
  ));
}
/* End projection utils */

// apply desaturation
vec3 color_desaturate(vec3 color) {
  float luminance = (color.r + color.g + color.b) * 0.333333333;
  return mix(color, vec3(luminance), bitmap.desaturate);
}

// apply tint
vec3 color_tint(vec3 color) {
  return color * bitmap.tintColor;
}

// blend with background color
vec4 apply_opacity(vec3 color, float alpha) {
  if (bitmap.transparentColor.a == 0.0) {
    return vec4(color, alpha);
  }
  float blendedAlpha = alpha + bitmap.transparentColor.a * (1.0 - alpha);
  float highLightRatio = alpha / blendedAlpha;
  vec3 blendedRGB = mix(bitmap.transparentColor.rgb, color, highLightRatio);
  return vec4(blendedRGB, blendedAlpha);
}

vec2 getUV(vec2 pos) {
  return vec2(
    (pos.x - bitmap.bounds[0]) / (bitmap.bounds[2] - bitmap.bounds[0]),
    (pos.y - bitmap.bounds[3]) / (bitmap.bounds[1] - bitmap.bounds[3])
  );
}

${wl}

void main(void) {
  vec2 uv = vTexCoord;
  if (bitmap.coordinateConversion < -0.5) {
    vec2 lnglat = mercator_to_lnglat(vTexPos);
    uv = getUV(lnglat);
  } else if (bitmap.coordinateConversion > 0.5) {
    vec2 commonPos = lnglat_to_mercator(vTexPos);
    uv = getUV(commonPos);
  }
  vec4 bitmapColor = texture(bitmapTexture, uv);

  fragColor = apply_opacity(color_tint(color_desaturate(bitmapColor.rgb)), bitmapColor.a * layer.opacity);

  geometry.uv = uv;
  DECKGL_FILTER_COLOR(fragColor, geometry);

  if (bool(picking.isActive) && !bool(picking.isAttribute)) {
    // Since instance information is not used, we can use picking color for pixel index
    fragColor.rgb = packUVsIntoRGB(uv);
  }
}
`,Sl={image:{type:"image",value:null,async:!0},bounds:{type:"array",value:[1,0,0,1],compare:!0},_imageCoordinateSystem:"default",desaturate:{type:"number",min:0,max:1,value:0},transparentColor:{type:"color",value:[0,0,0,0]},tintColor:{type:"color",value:[255,255,255]},textureParameters:{type:"object",ignore:!0,value:null}};class so extends N{getShaders(){return super.getShaders({vs:Ll,fs:Al,modules:[V,W,Cl]})}initializeState(){const t=this.getAttributeManager();t.remove(["instancePickingColors"]);const e=!0;t.add({indices:{size:1,isIndexed:!0,update:i=>i.value=this.state.mesh.indices,noAlloc:e},positions:{size:3,type:"float64",fp64:this.use64bitPositions(),update:i=>i.value=this.state.mesh.positions,noAlloc:e},texCoords:{size:2,update:i=>i.value=this.state.mesh.texCoords,noAlloc:e}})}updateState({props:t,oldProps:e,changeFlags:i}){var s;const o=this.getAttributeManager();if(i.extensionsChanged&&((s=this.state.model)==null||s.destroy(),this.state.model=this._getModel(),o.invalidateAll()),t.bounds!==e.bounds){const r=this.state.mesh,a=this._createMesh();this.state.model.setVertexCount(a.vertexCount);for(const l in a)r&&r[l]!==a[l]&&o.invalidate(l);this.setState({mesh:a,...this._getCoordinateUniforms()})}else t._imageCoordinateSystem!==e._imageCoordinateSystem&&this.setState(this._getCoordinateUniforms())}getPickingInfo(t){const{image:e}=this.props,i=t.info;if(!i.color||!e)return i.bitmap=null,i;const{width:o,height:s}=e;i.index=0;const r=Tl(i.color);return i.bitmap={size:{width:o,height:s},uv:r,pixel:[Math.floor(r[0]*o),Math.floor(r[1]*s)]},i}disablePickingIndex(){this.setState({disablePicking:!0})}restorePickingColors(){this.setState({disablePicking:!1})}_updateAutoHighlight(t){super._updateAutoHighlight({...t,color:this.encodePickingColor(0)})}_createMesh(){const{bounds:t}=this.props;let e=t;return Ni(t)&&(e=[[t[0],t[1]],[t[0],t[3]],[t[2],t[3]],[t[2],t[1]]]),xl(e,this.context.viewport.resolution)}_getModel(){return new z(this.context.device,{...this.getShaders(),id:this.props.id,bufferLayout:this.getAttributeManager().getBufferLayouts(),topology:"triangle-list",isInstanced:!1})}draw(t){const{shaderModuleProps:e}=t,{model:i,coordinateConversion:o,bounds:s,disablePicking:r}=this.state,{image:a,desaturate:l,transparentColor:c,tintColor:u}=this.props;if(!(e.picking.isActive&&r)&&a&&i){const f={bitmapTexture:a,bounds:s,coordinateConversion:o,desaturate:l,tintColor:u.slice(0,3).map(d=>d/255),transparentColor:c.map(d=>d/255)};i.shaderInputs.setProps({bitmap:f}),i.draw(this.context.renderPass)}}_getCoordinateUniforms(){let{_imageCoordinateSystem:t}=this.props;if(t!=="default"){const{bounds:e}=this.props;if(!Ni(e))throw new Error("_imageCoordinateSystem only supports rectangular bounds");const i=this.context.viewport.resolution?"lnglat":"cartesian";if(t=t==="lnglat"?"lnglat":"cartesian",t==="lnglat"&&i==="cartesian")return{coordinateConversion:-1,bounds:e};if(t==="cartesian"&&i==="lnglat"){const o=fi([e[0],e[1]]),s=fi([e[2],e[3]]);return{coordinateConversion:1,bounds:[o[0],o[1],s[0],s[1]]}}}return{coordinateConversion:0,bounds:[0,0,0,0]}}}so.layerName="BitmapLayer";so.defaultProps=Sl;function Tl(n){const[t,e,i]=n,o=(i&240)/256,s=(i&15)/16;return[(t+s)/256,(e+o)/256]}function Ni(n){return Number.isFinite(n[0])}const Ui=`layout(std140) uniform iconUniforms {
  float sizeScale;
  vec2 iconsTextureDim;
  float sizeBasis;
  float sizeMinPixels;
  float sizeMaxPixels;
  bool billboard;
  highp int sizeUnits;
  float alphaCutoff;
} icon;
`,El={name:"icon",vs:Ui,fs:Ui,uniformTypes:{sizeScale:"f32",iconsTextureDim:"vec2<f32>",sizeBasis:"f32",sizeMinPixels:"f32",sizeMaxPixels:"f32",billboard:"f32",sizeUnits:"i32",alphaCutoff:"f32"}},Il=`#version 300 es
#define SHADER_NAME icon-layer-vertex-shader
in vec2 positions;
in vec3 instancePositions;
in vec3 instancePositions64Low;
in float instanceSizes;
in float instanceAngles;
in vec4 instanceColors;
in vec3 instancePickingColors;
in vec4 instanceIconFrames;
in float instanceColorModes;
in vec2 instanceOffsets;
in vec2 instancePixelOffset;
out float vColorMode;
out vec4 vColor;
out vec2 vTextureCoords;
out vec2 uv;
vec2 rotate_by_angle(vec2 vertex, float angle) {
float angle_radian = angle * PI / 180.0;
float cos_angle = cos(angle_radian);
float sin_angle = sin(angle_radian);
mat2 rotationMatrix = mat2(cos_angle, -sin_angle, sin_angle, cos_angle);
return rotationMatrix * vertex;
}
void main(void) {
geometry.worldPosition = instancePositions;
geometry.uv = positions;
geometry.pickingColor = instancePickingColors;
uv = positions;
vec2 iconSize = instanceIconFrames.zw;
float sizePixels = clamp(
project_size_to_pixel(instanceSizes * icon.sizeScale, icon.sizeUnits),
icon.sizeMinPixels, icon.sizeMaxPixels
);
float iconConstraint = icon.sizeBasis == 0.0 ? iconSize.x : iconSize.y;
float instanceScale = iconConstraint == 0.0 ? 0.0 : sizePixels / iconConstraint;
vec2 pixelOffset = positions / 2.0 * iconSize + instanceOffsets;
pixelOffset = rotate_by_angle(pixelOffset, instanceAngles) * instanceScale;
pixelOffset += instancePixelOffset;
pixelOffset.y *= -1.0;
if (icon.billboard)  {
gl_Position = project_position_to_clipspace(instancePositions, instancePositions64Low, vec3(0.0), geometry.position);
DECKGL_FILTER_GL_POSITION(gl_Position, geometry);
vec3 offset = vec3(pixelOffset, 0.0);
DECKGL_FILTER_SIZE(offset, geometry);
gl_Position.xy += project_pixel_size_to_clipspace(offset.xy);
} else {
vec3 offset_common = vec3(project_pixel_size(pixelOffset), 0.0);
DECKGL_FILTER_SIZE(offset_common, geometry);
gl_Position = project_position_to_clipspace(instancePositions, instancePositions64Low, offset_common, geometry.position);
DECKGL_FILTER_GL_POSITION(gl_Position, geometry);
}
vTextureCoords = mix(
instanceIconFrames.xy,
instanceIconFrames.xy + iconSize,
(positions.xy + 1.0) / 2.0
) / icon.iconsTextureDim;
vColor = instanceColors;
DECKGL_FILTER_COLOR(vColor, geometry);
vColorMode = instanceColorModes;
}
`,Ol=`#version 300 es
#define SHADER_NAME icon-layer-fragment-shader
precision highp float;
uniform sampler2D iconsTexture;
in float vColorMode;
in vec4 vColor;
in vec2 vTextureCoords;
in vec2 uv;
out vec4 fragColor;
void main(void) {
geometry.uv = uv;
vec4 texColor = texture(iconsTexture, vTextureCoords);
vec3 color = mix(texColor.rgb, vColor.rgb, vColorMode);
float a = texColor.a * layer.opacity * vColor.a;
if (a < icon.alphaCutoff) {
discard;
}
fragColor = vec4(color, a);
DECKGL_FILTER_COLOR(fragColor, geometry);
}
`,Ml=`struct IconUniforms {
  sizeScale: f32,
  iconsTextureDim: vec2<f32>,
  sizeBasis: f32,
  sizeMinPixels: f32,
  sizeMaxPixels: f32,
  billboard: i32,
  sizeUnits: i32,
  alphaCutoff: f32
};

@group(0) @binding(auto) var<uniform> icon: IconUniforms;
@group(0) @binding(auto) var iconsTexture : texture_2d<f32>;
@group(0) @binding(auto) var iconsTextureSampler : sampler;

fn rotate_by_angle(vertex: vec2<f32>, angle_deg: f32) -> vec2<f32> {
  let angle_radian = angle_deg * PI / 180.0;
  let c = cos(angle_radian);
  let s = sin(angle_radian);
  let rotation = mat2x2<f32>(vec2<f32>(c, s), vec2<f32>(-s, c));
  return rotation * vertex;
}

struct Attributes {
  @location(0) positions: vec2<f32>,

  @location(1) instancePositions: vec3<f32>,
  @location(2) instancePositions64Low: vec3<f32>,
  @location(3) instanceSizes: f32,
  @location(4) instanceAngles: f32,
  @location(5) instanceColors: vec4<f32>,
  @location(6) instancePickingColors: vec3<f32>,
  @location(7) instanceIconFrames: vec4<f32>,
  @location(8) instanceColorModes: f32,
  @location(9) instanceOffsets: vec2<f32>,
  @location(10) instancePixelOffset: vec2<f32>,
};

struct Varyings {
  @builtin(position) position: vec4<f32>,

  @location(0) vColorMode: f32,
  @location(1) vColor: vec4<f32>,
  @location(2) vTextureCoords: vec2<f32>,
  @location(3) uv: vec2<f32>,
  @location(4) pickingColor: vec3<f32>,
};

@vertex
fn vertexMain(inp: Attributes) -> Varyings {
  // write geometry fields used by filters + FS
  geometry.worldPosition = inp.instancePositions;
  geometry.uv = inp.positions;
  geometry.pickingColor = inp.instancePickingColors;

  var outp: Varyings;
  outp.uv = inp.positions;

  let iconSize = inp.instanceIconFrames.zw;

  // convert size in meters to pixels, then clamp
  let sizePixels = clamp(
    project_unit_size_to_pixel(inp.instanceSizes * icon.sizeScale, icon.sizeUnits),
    icon.sizeMinPixels, icon.sizeMaxPixels
  );

  // scale icon height to match instanceSize
  let iconConstraint = select(iconSize.y, iconSize.x, icon.sizeBasis == 0.0);
  let instanceScale = select(sizePixels / iconConstraint, 0.0, iconConstraint == 0.0);

  // scale and rotate vertex in "pixel" units; then add per-instance pixel offset
  var pixelOffset = inp.positions / 2.0 * iconSize + inp.instanceOffsets;
  pixelOffset = rotate_by_angle(pixelOffset, inp.instanceAngles) * instanceScale;
  pixelOffset = pixelOffset + inp.instancePixelOffset;
  pixelOffset.y = pixelOffset.y * -1.0;

  if (icon.billboard != 0) {
    var pos = project_position_to_clipspace(inp.instancePositions, inp.instancePositions64Low, vec3<f32>(0.0)); // TODO, &geometry.position);
    // DECKGL_FILTER_GL_POSITION(pos, geometry);

    var offset = vec3<f32>(pixelOffset, 0.0);
    // DECKGL_FILTER_SIZE(offset, geometry);
    let clipOffset = project_pixel_size_to_clipspace(offset.xy);
    pos = vec4<f32>(pos.x + clipOffset.x, pos.y + clipOffset.y, pos.z, pos.w);
    outp.position = pos;
  } else {
    var offset_common = vec3<f32>(project_pixel_size_vec2(pixelOffset), 0.0);
    // DECKGL_FILTER_SIZE(offset_common, geometry);
    var pos = project_position_to_clipspace(inp.instancePositions, inp.instancePositions64Low, offset_common); // TODO, &geometry.position);
    // DECKGL_FILTER_GL_POSITION(pos, geometry);
    outp.position = pos;
  }

  let uvMix = (inp.positions.xy + vec2<f32>(1.0, 1.0)) * 0.5;
  outp.vTextureCoords = mix(inp.instanceIconFrames.xy, inp.instanceIconFrames.xy + iconSize, uvMix) / icon.iconsTextureDim;

  outp.vColor = inp.instanceColors;
  // DECKGL_FILTER_COLOR(outp.vColor, geometry);

  outp.vColorMode = inp.instanceColorModes;
  outp.pickingColor = inp.instancePickingColors;

  return outp;
}

@fragment
fn fragmentMain(inp: Varyings) -> @location(0) vec4<f32> {
  // expose to deck.gl filter hooks
  geometry.uv = inp.uv;

  let texColor = textureSample(iconsTexture, iconsTextureSampler, inp.vTextureCoords);

  // if colorMode == 0, use pixel color from the texture
  // if colorMode == 1 (or picking), use texture as transparency mask
  let rgb = mix(texColor.rgb, inp.vColor.rgb, inp.vColorMode);
  let a = texColor.a * layer.opacity * inp.vColor.a;

  if (a < icon.alphaCutoff) {
    discard;
  }

  if (picking.isActive > 0.5) {
    if (!picking_isColorValid(inp.pickingColor)) {
      discard;
    }
    return vec4<f32>(inp.pickingColor, 1.0);
  }

  var fragColor = deckgl_premultiplied_alpha(vec4<f32>(rgb, a));

  if (picking.isHighlightActive > 0.5) {
    let highlightedObjectColor = picking_normalizeColor(picking.highlightedObjectColor);
    if (picking_isColorZero(abs(inp.pickingColor - highlightedObjectColor))) {
      let highLightAlpha = picking.highlightColor.a;
      let blendedAlpha = highLightAlpha + fragColor.a * (1.0 - highLightAlpha);
      if (blendedAlpha > 0.0) {
        let highLightRatio = highLightAlpha / blendedAlpha;
        fragColor = vec4<f32>(
          mix(fragColor.rgb, picking.highlightColor.rgb, highLightRatio),
          blendedAlpha
        );
      } else {
        fragColor = vec4<f32>(fragColor.rgb, 0.0);
      }
    }
  }

  return fragColor;
}
`,Rl=1024,zl=4,Di=()=>{},ji={minFilter:"linear",mipmapFilter:"linear",magFilter:"linear",addressModeU:"clamp-to-edge",addressModeV:"clamp-to-edge"},Fl={x:0,y:0,width:0,height:0};function kl(n){return Math.pow(2,Math.ceil(Math.log2(n)))}function Bl(n,t,e,i){const o=Math.min(e/t.width,i/t.height),s=Math.floor(t.width*o),r=Math.floor(t.height*o);return o===1?{image:t,width:s,height:r}:(n.canvas.height=r,n.canvas.width=s,n.clearRect(0,0,s,r),n.drawImage(t,0,0,t.width,t.height,0,0,s,r),{image:n.canvas,width:s,height:r})}function Pt(n){return n&&(n.id||n.url)}function ro(n){const{device:t}=n;t.type==="webgl"?n.generateMipmapsWebGL():t.type==="webgpu"&&t.generateMipmapsWebGPU(n)}function Nl(n,t,e,i){const{width:o,height:s,device:r}=n,a=r.createTexture({format:"rgba8unorm",width:t,height:e,sampler:i,mipLevels:r.getMipLevelCount(t,e)}),l=r.createCommandEncoder();l.copyTextureToTexture({sourceTexture:n,destinationTexture:a,width:o,height:s});const c=l.finish();return r.submit(c),ro(a),n.destroy(),a}function Gi(n,t,e){for(let i=0;i<t.length;i++){const{icon:o,xOffset:s}=t[i],r=Pt(o);n[r]={...o,x:s,y:e}}}function Ul({icons:n,buffer:t,mapping:e={},xOffset:i=0,yOffset:o=0,rowHeight:s=0,canvasWidth:r}){let a=[];for(let l=0;l<n.length;l++){const c=n[l],u=Pt(c);if(!e[u]){const{height:f,width:d}=c;i+d+t>r&&(Gi(e,a,o),i=0,o=s+o+t,s=0,a=[]),a.push({icon:c,xOffset:i}),i=i+d+t,s=Math.max(s,f)}}return a.length>0&&Gi(e,a,o),{mapping:e,rowHeight:s,xOffset:i,yOffset:o,canvasWidth:r,canvasHeight:kl(s+o+t)}}function Dl(n,t,e){if(!n||!t)return null;e=e||{};const i={},{iterable:o,objectInfo:s}=ct(n);for(const r of o){s.index++;const a=t(r,s),l=Pt(a);if(!a)throw new Error("Icon is missing.");if(!a.url)throw new Error("Icon url is missing.");!i[l]&&(!e[l]||a.url!==e[l].url)&&(i[l]={...a,source:r,sourceIndex:s.index})}return i}class jl{constructor(t,{onUpdate:e=Di,onError:i=Di}){this._loadOptions=null,this._texture=null,this._externalTexture=null,this._mapping={},this._samplerParameters=null,this._pendingCount=0,this._autoPacking=!1,this._xOffset=0,this._yOffset=0,this._rowHeight=0,this._buffer=zl,this._canvasWidth=Rl,this._canvasHeight=0,this._canvas=null,this.device=t,this.onUpdate=e,this.onError=i}finalize(){var t;(t=this._texture)==null||t.delete()}getTexture(){return this._texture||this._externalTexture}getIconMapping(t){const e=this._autoPacking?Pt(t):t;return this._mapping[e]||Fl}setProps({loadOptions:t,autoPacking:e,iconAtlas:i,iconMapping:o,textureParameters:s}){var r;t&&(this._loadOptions=t),e!==void 0&&(this._autoPacking=e),o&&(this._mapping=o),i&&((r=this._texture)==null||r.delete(),this._texture=null,this._externalTexture=i),s&&(this._samplerParameters=s)}get isLoaded(){return this._pendingCount===0}packIcons(t,e){if(!this._autoPacking||typeof document>"u")return;const i=Object.values(Dl(t,e,this._mapping)||{});if(i.length>0){const{mapping:o,xOffset:s,yOffset:r,rowHeight:a,canvasHeight:l}=Ul({icons:i,buffer:this._buffer,canvasWidth:this._canvasWidth,mapping:this._mapping,rowHeight:this._rowHeight,xOffset:this._xOffset,yOffset:this._yOffset});this._rowHeight=a,this._mapping=o,this._xOffset=s,this._yOffset=r,this._canvasHeight=l,this._texture||(this._texture=this.device.createTexture({format:"rgba8unorm",data:null,width:this._canvasWidth,height:this._canvasHeight,sampler:this._samplerParameters||ji,mipLevels:this.device.getMipLevelCount(this._canvasWidth,this._canvasHeight)})),this._texture.height!==this._canvasHeight&&(this._texture=Nl(this._texture,this._canvasWidth,this._canvasHeight,this._samplerParameters||ji)),this.onUpdate(!0),this._canvas=this._canvas||document.createElement("canvas"),this._loadIcons(i)}}_loadIcons(t){const e=this._canvas.getContext("2d",{willReadFrequently:!0});for(const i of t)this._pendingCount++,Oe(i.url,this._loadOptions).then(o=>{var m;const s=Pt(i),r=this._mapping[s],{x:a,y:l,width:c,height:u}=r,{image:f,width:d,height:h}=Bl(e,o,c,u),p=a+(c-d)/2,g=l+(u-h)/2;(m=this._texture)==null||m.copyExternalImage({image:f,x:p,y:g,width:d,height:h}),r.x=p,r.y=g,r.width=d,r.height=h,this._texture&&ro(this._texture),this.onUpdate(d!==c||h!==u)}).catch(o=>{this.onError({url:i.url,source:i.source,sourceIndex:i.sourceIndex,loadOptions:this._loadOptions,error:o})}).finally(()=>{this._pendingCount--})}}const ao=[0,0,0,255],Gl={iconAtlas:{type:"image",value:null,async:!0},iconMapping:{type:"object",value:{},async:!0},sizeScale:{type:"number",value:1,min:0},billboard:!0,sizeUnits:"pixels",sizeBasis:"height",sizeMinPixels:{type:"number",min:0,value:0},sizeMaxPixels:{type:"number",min:0,value:Number.MAX_SAFE_INTEGER},alphaCutoff:{type:"number",value:.05,min:0,max:1},getPosition:{type:"accessor",value:n=>n.position},getIcon:{type:"accessor",value:n=>n.icon},getColor:{type:"accessor",value:ao},getSize:{type:"accessor",value:1},getAngle:{type:"accessor",value:0},getPixelOffset:{type:"accessor",value:[0,0]},onIconError:{type:"function",value:null,optional:!0},textureParameters:{type:"object",ignore:!0,value:null}};class fe extends N{getShaders(){return super.getShaders({vs:Il,fs:Ol,source:Ml,modules:[V,le,W,El]})}initializeState(){this.state={iconManager:new jl(this.context.device,{onUpdate:this._onUpdate.bind(this),onError:this._onError.bind(this)})},this.getAttributeManager().addInstanced({instancePositions:{size:3,type:"float64",fp64:this.use64bitPositions(),transition:!0,accessor:"getPosition"},instanceSizes:{size:1,transition:!0,accessor:"getSize",defaultValue:1},instanceIconDefs:{size:7,accessor:"getIcon",transform:this.getInstanceIconDef,shaderAttributes:{instanceOffsets:{size:2,elementOffset:0},instanceIconFrames:{size:4,elementOffset:2},instanceColorModes:{size:1,elementOffset:6}}},instanceColors:{size:this.props.colorFormat.length,type:"unorm8",transition:!0,accessor:"getColor",defaultValue:ao},instanceAngles:{size:1,transition:!0,accessor:"getAngle"},instancePixelOffset:{size:2,transition:!0,accessor:"getPixelOffset"}})}updateState(t){var h;super.updateState(t);const{props:e,oldProps:i,changeFlags:o}=t,s=this.getAttributeManager(),{iconAtlas:r,iconMapping:a,data:l,getIcon:c,textureParameters:u}=e,{iconManager:f}=this.state;if(typeof r=="string")return;const d=r||this.internalState.isAsyncPropLoading("iconAtlas");f.setProps({loadOptions:e.loadOptions,autoPacking:!d,iconAtlas:r,iconMapping:d?a:null,textureParameters:u}),d?i.iconMapping!==e.iconMapping&&s.invalidate("getIcon"):(o.dataChanged||o.updateTriggersChanged&&(o.updateTriggersChanged.all||o.updateTriggersChanged.getIcon))&&f.packIcons(l,c),o.extensionsChanged&&((h=this.state.model)==null||h.destroy(),this.state.model=this._getModel(),s.invalidateAll())}get isLoaded(){return super.isLoaded&&this.state.iconManager.isLoaded}finalizeState(t){super.finalizeState(t),this.state.iconManager.finalize()}draw({uniforms:t}){const{sizeScale:e,sizeBasis:i,sizeMinPixels:o,sizeMaxPixels:s,sizeUnits:r,billboard:a,alphaCutoff:l}=this.props,{iconManager:c}=this.state,u=c.getTexture();if(u){const f=this.state.model,d={iconsTexture:u,iconsTextureDim:[u.width,u.height],sizeUnits:G[r],sizeScale:e,sizeBasis:i==="height"?1:0,sizeMinPixels:o,sizeMaxPixels:s,billboard:a,alphaCutoff:l};f.shaderInputs.setProps({icon:d}),f.draw(this.context.renderPass)}}_getModel(){const t=[-1,-1,1,-1,-1,1,1,1];return new z(this.context.device,{...this.getShaders(),id:this.props.id,bufferLayout:this.getAttributeManager().getBufferLayouts(),geometry:new $({topology:"triangle-strip",attributes:{positions:{size:2,value:new Float32Array(t)}}}),isInstanced:!0})}_onUpdate(t){var e;t?((e=this.getAttributeManager())==null||e.invalidate("getIcon"),this.setNeedsUpdate()):this.setNeedsRedraw()}_onError(t){var i;const e=(i=this.getCurrentLayer())==null?void 0:i.props.onIconError;e?e(t):T.error(t.error.message)()}getInstanceIconDef(t){const{x:e,y:i,width:o,height:s,mask:r,anchorX:a=o/2,anchorY:l=s/2}=this.state.iconManager.getIconMapping(t);return[o/2-a,s/2-l,e,i,o,s,r?1:0]}}fe.defaultProps=Gl;fe.layerName="IconLayer";const $i=`layout(std140) uniform lineUniforms {
  float widthScale;
  float widthMinPixels;
  float widthMaxPixels;
  float useShortestPath;
  highp int widthUnits;
} line;
`,$l={name:"line",source:"",vs:$i,fs:$i,uniformTypes:{widthScale:"f32",widthMinPixels:"f32",widthMaxPixels:"f32",useShortestPath:"f32",widthUnits:"i32"}},Vl=`// ---------- Helper Structures & Functions ----------

// Placeholder filter functions.
fn deckgl_filter_size(offset: vec3<f32>, geometry: Geometry) -> vec3<f32> {
  return offset;
}
fn deckgl_filter_gl_position(p: vec4<f32>, geometry: Geometry) -> vec4<f32> {
  if (picking.isAttribute > 0.5) {
    // For depth picking, write normalized depth into the picking payload.
    // This mirrors the legacy DECKGL_FILTER_GL_POSITION hook on WebGL.
  }
  return p;
}

// Compute an extrusion offset given a line direction (in clipspace),
// an offset direction (-1 or 1), and a width in pixels.
// Assumes a uniform "project" with a viewportSize field is available.
fn getExtrusionOffset(line_clipspace: vec2<f32>, offset_direction: f32, width: f32) -> vec2<f32> {
  // project.viewportSize should be provided as a uniform (not shown here)
  let dir_screenspace = normalize(line_clipspace * project.viewportSize);
  // Rotate by 90°: (x,y) becomes (-y,x)
  let rotated = vec2<f32>(-dir_screenspace.y, dir_screenspace.x);
  return rotated * offset_direction * width / 2.0;
}

// Splits the line between two points at a given x coordinate.
// Interpolates the y and z components.
fn splitLine(a: vec3<f32>, b: vec3<f32>, x: f32) -> vec3<f32> {
  let t: f32 = (x - a.x) / (b.x - a.x);
  return vec3<f32>(x, a.yz + t * (b.yz - a.yz));
}

// ---------- Uniforms & Global Structures ----------

struct LineUniforms {
  widthScale: f32,
  widthMinPixels: f32,
  widthMaxPixels: f32,
  useShortestPath: f32,
  widthUnits: i32,
};

@group(0) @binding(0)
var<uniform> line: LineUniforms;



// ---------- Vertex Output Structure ----------

struct Varyings {
  @builtin(position) gl_Position: vec4<f32>,
  @location(0) vColor: vec4<f32>,
  @location(1) uv: vec2<f32>,
  @location(2) pickingColor: vec3<f32>,
};

// ---------- Vertex Shader Entry Point ----------

@vertex
fn vertexMain(
  @location(0) positions: vec3<f32>,
  @location(1) instanceSourcePositions: vec3<f32>,
  @location(2) instanceTargetPositions: vec3<f32>,
  @location(3) instanceSourcePositions64Low: vec3<f32>,
  @location(4) instanceTargetPositions64Low: vec3<f32>,
  @location(5) instanceColors: vec4<f32>,
  @location(6) instancePickingColors: vec3<f32>,
  @location(7) instanceWidths: f32
) -> Varyings {
  geometry.worldPosition = instanceSourcePositions;
  geometry.worldPositionAlt = instanceTargetPositions;

  var source_world: vec3<f32> = instanceSourcePositions;
  var target_world: vec3<f32> = instanceTargetPositions;
  var source_world_64low: vec3<f32> = instanceSourcePositions64Low;
  var target_world_64low: vec3<f32> = instanceTargetPositions64Low;

  // Apply shortest-path adjustments if needed.
  if (line.useShortestPath > 0.5 || line.useShortestPath < -0.5) {
    source_world.x = (source_world.x + 180.0 % 360.0) - 180.0;
    target_world.x = (target_world.x + 180.0 % 360.0) - 180.0;
    let deltaLng: f32 = target_world.x - source_world.x;

    if (deltaLng * line.useShortestPath > 180.0) {
      source_world.x = source_world.x + 360.0 * line.useShortestPath;
      source_world = splitLine(source_world, target_world, 180.0 * line.useShortestPath);
      source_world_64low = vec3<f32>(0.0, 0.0, 0.0);
    } else if (deltaLng * line.useShortestPath < -180.0) {
      target_world.x = target_world.x + 360.0 * line.useShortestPath;
      target_world = splitLine(source_world, target_world, 180.0 * line.useShortestPath);
      target_world_64low = vec3<f32>(0.0, 0.0, 0.0);
    } else if (line.useShortestPath < 0.0) {
      var abortOut: Varyings;
      abortOut.gl_Position = vec4<f32>(0.0);
      abortOut.vColor = vec4<f32>(0.0);
      abortOut.uv = vec2<f32>(0.0);
      return abortOut;
    }
  }

  // Project Pos and target positions to clip space.
  let sourceResult = project_position_to_clipspace_and_commonspace(source_world, source_world_64low, vec3<f32>(0.0));
  let targetResult = project_position_to_clipspace_and_commonspace(target_world, target_world_64low, vec3<f32>(0.0));
  let sourcePos: vec4<f32> = sourceResult.clipPosition;
  let targetPos: vec4<f32> = targetResult.clipPosition;
  let source_commonspace: vec4<f32> = sourceResult.commonPosition;
  let target_commonspace: vec4<f32> = targetResult.commonPosition;

  // Interpolate along the line segment.
  let segmentIndex: f32 = positions.x;
  let p: vec4<f32> = sourcePos + segmentIndex * (targetPos - sourcePos);
  geometry.position = source_commonspace + segmentIndex * (target_commonspace - source_commonspace);
  let uv: vec2<f32> = positions.xy;
  geometry.uv = uv;
  geometry.pickingColor = instancePickingColors;

  // Determine width in pixels.
  let widthPixels: f32 = clamp(
    project_unit_size_to_pixel(instanceWidths * line.widthScale, line.widthUnits),
    line.widthMinPixels, line.widthMaxPixels
  );

  // Compute extrusion offset.
  let extrusion: vec2<f32> = getExtrusionOffset(targetPos.xy - sourcePos.xy, positions.y, widthPixels);
  let offset: vec3<f32> = vec3<f32>(extrusion, 0.0);

  // Apply deck.gl filter functions.
  let filteredOffset = deckgl_filter_size(offset, geometry);
  let filteredP = deckgl_filter_gl_position(p, geometry);

  let clipOffset: vec2<f32> = project_pixel_size_to_clipspace(filteredOffset.xy);
  let finalPosition: vec4<f32> = filteredP + vec4<f32>(clipOffset, 0.0, 0.0);

  // Compute color.
  var vColor: vec4<f32> = vec4<f32>(instanceColors.rgb, instanceColors.a * layer.opacity);
  // vColor = deckgl_filter_color(vColor, geometry);

  var output: Varyings;
  output.gl_Position = finalPosition;
  output.vColor = vColor;
  output.uv = uv;
  output.pickingColor = instancePickingColors;
  return output;
}

@fragment
fn fragmentMain(
  @location(0) vColor: vec4<f32>,
  @location(1) uv: vec2<f32>,
  @location(2) pickingColor: vec3<f32>
) -> @location(0) vec4<f32> {
  // Create and initialize geometry with the provided uv.
  var geometry: Geometry;
  geometry.uv = uv;

  // Start with the input color.
  var fragColor: vec4<f32> = vColor;

  if (picking.isActive > 0.5) {
    if (!picking_isColorValid(pickingColor)) {
      discard;
    }
    return vec4<f32>(pickingColor, 1.0);
  }

  if (picking.isHighlightActive > 0.5) {
    let highlightedObjectColor = picking_normalizeColor(picking.highlightedObjectColor);
    if (picking_isColorZero(abs(pickingColor - highlightedObjectColor))) {
      let highLightAlpha = picking.highlightColor.a;
      let blendedAlpha = highLightAlpha + fragColor.a * (1.0 - highLightAlpha);
      if (blendedAlpha > 0.0) {
        let highLightRatio = highLightAlpha / blendedAlpha;
        fragColor = vec4<f32>(
          mix(fragColor.rgb, picking.highlightColor.rgb, highLightRatio),
          blendedAlpha
        );
      } else {
        fragColor = vec4<f32>(fragColor.rgb, 0.0);
      }
    }
  }

  // Apply premultiplied alpha as required by transparent canvas
  fragColor = deckgl_premultiplied_alpha(fragColor);

  return fragColor;
}
`,Wl=`#version 300 es
#define SHADER_NAME line-layer-vertex-shader
in vec3 positions;
in vec3 instanceSourcePositions;
in vec3 instanceTargetPositions;
in vec3 instanceSourcePositions64Low;
in vec3 instanceTargetPositions64Low;
in vec4 instanceColors;
in vec3 instancePickingColors;
in float instanceWidths;
out vec4 vColor;
out vec2 uv;
vec2 getExtrusionOffset(vec2 line_clipspace, float offset_direction, float width) {
vec2 dir_screenspace = normalize(line_clipspace * project.viewportSize);
dir_screenspace = vec2(-dir_screenspace.y, dir_screenspace.x);
return dir_screenspace * offset_direction * width / 2.0;
}
vec3 splitLine(vec3 a, vec3 b, float x) {
float t = (x - a.x) / (b.x - a.x);
return vec3(x, mix(a.yz, b.yz, t));
}
void main(void) {
geometry.worldPosition = instanceSourcePositions;
geometry.worldPositionAlt = instanceTargetPositions;
vec3 source_world = instanceSourcePositions;
vec3 target_world = instanceTargetPositions;
vec3 source_world_64low = instanceSourcePositions64Low;
vec3 target_world_64low = instanceTargetPositions64Low;
if (line.useShortestPath > 0.5 || line.useShortestPath < -0.5) {
source_world.x = mod(source_world.x + 180., 360.0) - 180.;
target_world.x = mod(target_world.x + 180., 360.0) - 180.;
float deltaLng = target_world.x - source_world.x;
if (deltaLng * line.useShortestPath > 180.) {
source_world.x += 360. * line.useShortestPath;
source_world = splitLine(source_world, target_world, 180. * line.useShortestPath);
source_world_64low = vec3(0.0);
} else if (deltaLng * line.useShortestPath < -180.) {
target_world.x += 360. * line.useShortestPath;
target_world = splitLine(source_world, target_world, 180. * line.useShortestPath);
target_world_64low = vec3(0.0);
} else if (line.useShortestPath < 0.) {
gl_Position = vec4(0.);
return;
}
}
vec4 source_commonspace;
vec4 target_commonspace;
vec4 source = project_position_to_clipspace(source_world, source_world_64low, vec3(0.), source_commonspace);
vec4 target = project_position_to_clipspace(target_world, target_world_64low, vec3(0.), target_commonspace);
float segmentIndex = positions.x;
vec4 p = mix(source, target, segmentIndex);
geometry.position = mix(source_commonspace, target_commonspace, segmentIndex);
uv = positions.xy;
geometry.uv = uv;
geometry.pickingColor = instancePickingColors;
float widthPixels = clamp(
project_size_to_pixel(instanceWidths * line.widthScale, line.widthUnits),
line.widthMinPixels, line.widthMaxPixels
);
vec3 offset = vec3(
getExtrusionOffset(target.xy - source.xy, positions.y, widthPixels),
0.0);
DECKGL_FILTER_SIZE(offset, geometry);
DECKGL_FILTER_GL_POSITION(p, geometry);
gl_Position = p + vec4(project_pixel_size_to_clipspace(offset.xy), 0.0, 0.0);
vColor = vec4(instanceColors.rgb, instanceColors.a * layer.opacity);
DECKGL_FILTER_COLOR(vColor, geometry);
}
`,Hl=`#version 300 es
#define SHADER_NAME line-layer-fragment-shader
precision highp float;
in vec4 vColor;
in vec2 uv;
out vec4 fragColor;
void main(void) {
geometry.uv = uv;
fragColor = vColor;
DECKGL_FILTER_COLOR(fragColor, geometry);
}
`,Kl=[0,0,0,255],Yl={getSourcePosition:{type:"accessor",value:n=>n.sourcePosition},getTargetPosition:{type:"accessor",value:n=>n.targetPosition},getColor:{type:"accessor",value:Kl},getWidth:{type:"accessor",value:1},widthUnits:"pixels",widthScale:{type:"number",value:1,min:0},widthMinPixels:{type:"number",value:0,min:0},widthMaxPixels:{type:"number",value:Number.MAX_SAFE_INTEGER,min:0}};class lo extends N{getBounds(){var t;return(t=this.getAttributeManager())==null?void 0:t.getBounds(["instanceSourcePositions","instanceTargetPositions"])}getShaders(){return super.getShaders({vs:Wl,fs:Hl,source:Vl,modules:[V,le,W,$l]})}get wrapLongitude(){return!1}initializeState(){this.getAttributeManager().addInstanced({instanceSourcePositions:{size:3,type:"float64",fp64:this.use64bitPositions(),transition:!0,accessor:"getSourcePosition"},instanceTargetPositions:{size:3,type:"float64",fp64:this.use64bitPositions(),transition:!0,accessor:"getTargetPosition"},instanceColors:{size:this.props.colorFormat.length,type:"unorm8",transition:!0,accessor:"getColor",defaultValue:[0,0,0,255]},instanceWidths:{size:1,transition:!0,accessor:"getWidth",defaultValue:1}})}updateState(t){var e;super.updateState(t),t.changeFlags.extensionsChanged&&((e=this.state.model)==null||e.destroy(),this.state.model=this._getModel(),this.getAttributeManager().invalidateAll())}draw({uniforms:t}){const{widthUnits:e,widthScale:i,widthMinPixels:o,widthMaxPixels:s,wrapLongitude:r}=this.props,a=this.state.model,l={widthUnits:G[e],widthScale:i,widthMinPixels:o,widthMaxPixels:s,useShortestPath:r?1:0};a.shaderInputs.setProps({line:l}),a.draw(this.context.renderPass),r&&(a.shaderInputs.setProps({line:{...l,useShortestPath:-1}}),a.draw(this.context.renderPass))}_getModel(){const t=[0,-1,0,0,1,0,1,-1,0,1,1,0];return new z(this.context.device,{...this.getShaders(),id:this.props.id,bufferLayout:this.getAttributeManager().getBufferLayouts(),geometry:new $({topology:"triangle-strip",attributes:{positions:{size:3,value:new Float32Array(t)}}}),isInstanced:!0})}}lo.layerName="LineLayer";lo.defaultProps=Yl;const Vi=`layout(std140) uniform pointCloudUniforms {
  float radiusPixels;
  highp int sizeUnits;
} pointCloud;
`,Zl={name:"pointCloud",source:"",vs:Vi,fs:Vi,uniformTypes:{radiusPixels:"f32",sizeUnits:"i32"}},ql=`#version 300 es
#define SHADER_NAME point-cloud-layer-vertex-shader
in vec3 positions;
in vec3 instanceNormals;
in vec4 instanceColors;
in vec3 instancePositions;
in vec3 instancePositions64Low;
in vec3 instancePickingColors;
out vec4 vColor;
out vec2 unitPosition;
void main(void) {
geometry.worldPosition = instancePositions;
geometry.normal = project_normal(instanceNormals);
unitPosition = positions.xy;
geometry.uv = unitPosition;
geometry.pickingColor = instancePickingColors;
vec3 offset = vec3(positions.xy * project_size_to_pixel(pointCloud.radiusPixels, pointCloud.sizeUnits), 0.0);
DECKGL_FILTER_SIZE(offset, geometry);
gl_Position = project_position_to_clipspace(instancePositions, instancePositions64Low, vec3(0.), geometry.position);
DECKGL_FILTER_GL_POSITION(gl_Position, geometry);
gl_Position.xy += project_pixel_size_to_clipspace(offset.xy);
vec3 lightColor = lighting_getLightColor(instanceColors.rgb, project.cameraPosition, geometry.position.xyz, geometry.normal);
vColor = vec4(lightColor, instanceColors.a * layer.opacity);
DECKGL_FILTER_COLOR(vColor, geometry);
}
`,Xl=`#version 300 es
#define SHADER_NAME point-cloud-layer-fragment-shader
precision highp float;
in vec4 vColor;
in vec2 unitPosition;
out vec4 fragColor;
void main(void) {
geometry.uv = unitPosition.xy;
float distToCenter = length(unitPosition);
if (distToCenter > 1.0) {
discard;
}
fragColor = vColor;
DECKGL_FILTER_COLOR(fragColor, geometry);
}
`,Jl=`struct PointCloudUniforms {
  radiusPixels: f32,
  sizeUnits: i32,
};

@group(0) @binding(0)
var<uniform> pointCloudUniforms: PointCloudUniforms;

struct ConstantAttributes {
  instanceNormals: vec3<f32>,
  instanceColors: vec4<f32>,
  instancePositions: vec3<f32>,
  instancePositions64Low: vec3<f32>,
  instancePickingColors: vec3<f32>
};

const constants = ConstantAttributes(
  vec3<f32>(1.0, 0.0, 0.0),
  vec4<f32>(0.0, 0.0, 0.0, 1.0),
  vec3<f32>(0.0),
  vec3<f32>(0.0),
  vec3<f32>(0.0)
);

struct Attributes {
  @builtin(instance_index) instanceIndex : u32,
  @builtin(vertex_index) vertexIndex : u32,
  @location(0) positions: vec3<f32>,
  @location(1) instancePositions: vec3<f32>,
  @location(2) instancePositions64Low: vec3<f32>,
  @location(3) instanceNormals: vec3<f32>,
  @location(4) instanceColors: vec4<f32>,
  @location(5) instancePickingColors: vec3<f32>
};

struct Varyings {
  @builtin(position) position: vec4<f32>,
  @location(0) vColor: vec4<f32>,
  @location(1) unitPosition: vec2<f32>,
  @location(2) pickingColor: vec3<f32>,
};

@vertex
fn vertexMain(attributes: Attributes) -> Varyings {
  var varyings: Varyings;

  geometry.worldPosition = attributes.instancePositions;

  let centerResult = project_position_to_clipspace_and_commonspace(
    attributes.instancePositions,
    attributes.instancePositions64Low,
    vec3<f32>(0.0)
  );
  geometry.position = centerResult.commonPosition;
  geometry.normal = project_normal(attributes.instanceNormals);

  // position on the containing square in [-1, 1] space
  varyings.unitPosition = attributes.positions.xy;
  geometry.uv = varyings.unitPosition;
  geometry.pickingColor = attributes.instancePickingColors;

  // Find the center of the point and add the current vertex
  let offset = vec3<f32>(
    attributes.positions.xy *
      project_unit_size_to_pixel(pointCloudUniforms.radiusPixels, pointCloudUniforms.sizeUnits),
    0.0
  );
  // DECKGL_FILTER_SIZE(offset, geometry);

  varyings.position = centerResult.clipPosition;
  // DECKGL_FILTER_GL_POSITION(gl_Position, geometry);
  let clipPixels = project_pixel_size_to_clipspace(offset.xy);
  varyings.position.x += clipPixels.x;
  varyings.position.y += clipPixels.y;

  // Apply lighting
  let lightColor = lighting_getLightColor2(attributes.instanceColors.rgb, project.cameraPosition, geometry.position.xyz, geometry.normal);

  // Apply opacity to instance color, or return instance picking color
  varyings.vColor = vec4(lightColor, attributes.instanceColors.a * layer.opacity);
  // DECKGL_FILTER_COLOR(vColor, geometry);
  varyings.pickingColor = attributes.instancePickingColors;

  return varyings;
}

@fragment
fn fragmentMain(varyings: Varyings) -> @location(0) vec4<f32> {
  // var geometry: Geometry;
  // geometry.uv = unitPosition.xy;

  let distToCenter = length(varyings.unitPosition);
  if (distToCenter > 1.0) {
    discard;
  }

  var fragColor: vec4<f32>;

  fragColor = varyings.vColor;

  if (picking.isActive > 0.5) {
    if (!picking_isColorValid(varyings.pickingColor)) {
      discard;
    }
    return vec4<f32>(varyings.pickingColor, 1.0);
  }

  if (picking.isHighlightActive > 0.5) {
    let highlightedObjectColor = picking_normalizeColor(picking.highlightedObjectColor);
    if (picking_isColorZero(abs(varyings.pickingColor - highlightedObjectColor))) {
      let highLightAlpha = picking.highlightColor.a;
      let blendedAlpha = highLightAlpha + fragColor.a * (1.0 - highLightAlpha);
      if (blendedAlpha > 0.0) {
        let highLightRatio = highLightAlpha / blendedAlpha;
        fragColor = vec4<f32>(
          mix(fragColor.rgb, picking.highlightColor.rgb, highLightRatio),
          blendedAlpha
        );
      } else {
        fragColor = vec4<f32>(fragColor.rgb, 0.0);
      }
    }
  }

  // Apply premultiplied alpha as required by transparent canvas
  fragColor = deckgl_premultiplied_alpha(fragColor);

  return fragColor;
}
`,co=[0,0,0,255],uo=[0,0,1],Ql={sizeUnits:"pixels",pointSize:{type:"number",min:0,value:10},getPosition:{type:"accessor",value:n=>n.position},getNormal:{type:"accessor",value:uo},getColor:{type:"accessor",value:co},material:!0,radiusPixels:{deprecatedFor:"pointSize"}};function tc(n){const{header:t,attributes:e}=n;if(!(!t||!e)&&(n.length=t.vertexCount,e.POSITION&&(e.instancePositions=e.POSITION),e.NORMAL&&(e.instanceNormals=e.NORMAL),e.COLOR_0)){const{size:i,value:o}=e.COLOR_0;e.instanceColors={size:i,type:"unorm8",value:o}}}class fo extends N{getShaders(){return super.getShaders({vs:ql,fs:Xl,source:Jl,modules:[V,le,ae,W,Zl]})}initializeState(){this.getAttributeManager().addInstanced({instancePositions:{size:3,type:"float64",fp64:this.use64bitPositions(),transition:!0,accessor:"getPosition"},instanceNormals:{size:3,transition:!0,accessor:"getNormal",defaultValue:uo},instanceColors:{size:this.props.colorFormat.length,type:"unorm8",transition:!0,accessor:"getColor",defaultValue:co}})}updateState(t){var o;const{changeFlags:e,props:i}=t;super.updateState(t),e.extensionsChanged&&((o=this.state.model)==null||o.destroy(),this.state.model=this._getModel(),this.getAttributeManager().invalidateAll()),e.dataChanged&&tc(i.data)}draw({uniforms:t}){const{pointSize:e,sizeUnits:i}=this.props,o=this.state.model,s={sizeUnits:G[i],radiusPixels:e};o.shaderInputs.setProps({pointCloud:s}),o.draw(this.context.renderPass)}_getModel(){const t=[];for(let e=0;e<3;e++){const i=e/3*Math.PI*2;t.push(Math.cos(i)*2,Math.sin(i)*2,0)}return new z(this.context.device,{...this.getShaders(),id:this.props.id,bufferLayout:this.getAttributeManager().getBufferLayouts(),geometry:new $({topology:"triangle-list",attributes:{positions:new Float32Array(t)}}),isInstanced:!0})}}fo.layerName="PointCloudLayer";fo.defaultProps=Ql;const Wi=`layout(std140) uniform scatterplotUniforms {
  float radiusScale;
  float radiusMinPixels;
  float radiusMaxPixels;
  float lineWidthScale;
  float lineWidthMinPixels;
  float lineWidthMaxPixels;
  float stroked;
  float filled;
  bool antialiasing;
  bool billboard;
  highp int radiusUnits;
  highp int lineWidthUnits;
} scatterplot;
`,ec={name:"scatterplot",vs:Wi,fs:Wi,source:"",uniformTypes:{radiusScale:"f32",radiusMinPixels:"f32",radiusMaxPixels:"f32",lineWidthScale:"f32",lineWidthMinPixels:"f32",lineWidthMaxPixels:"f32",stroked:"f32",filled:"f32",antialiasing:"f32",billboard:"f32",radiusUnits:"i32",lineWidthUnits:"i32"}},ic=`#version 300 es
#define SHADER_NAME scatterplot-layer-vertex-shader
in vec3 positions;
in vec3 instancePositions;
in vec3 instancePositions64Low;
in float instanceRadius;
in float instanceLineWidths;
in vec4 instanceFillColors;
in vec4 instanceLineColors;
in vec3 instancePickingColors;
out vec4 vFillColor;
out vec4 vLineColor;
out vec2 unitPosition;
out float innerUnitRadius;
out float outerRadiusPixels;
void main(void) {
geometry.worldPosition = instancePositions;
outerRadiusPixels = clamp(
project_size_to_pixel(scatterplot.radiusScale * instanceRadius, scatterplot.radiusUnits),
scatterplot.radiusMinPixels, scatterplot.radiusMaxPixels
);
float lineWidthPixels = clamp(
project_size_to_pixel(scatterplot.lineWidthScale * instanceLineWidths, scatterplot.lineWidthUnits),
scatterplot.lineWidthMinPixels, scatterplot.lineWidthMaxPixels
);
outerRadiusPixels += scatterplot.stroked * lineWidthPixels / 2.0;
float edgePadding = scatterplot.antialiasing ? (outerRadiusPixels + SMOOTH_EDGE_RADIUS) / outerRadiusPixels : 1.0;
unitPosition = edgePadding * positions.xy;
geometry.uv = unitPosition;
geometry.pickingColor = instancePickingColors;
innerUnitRadius = 1.0 - scatterplot.stroked * lineWidthPixels / outerRadiusPixels;
if (scatterplot.billboard) {
gl_Position = project_position_to_clipspace(instancePositions, instancePositions64Low, vec3(0.0), geometry.position);
DECKGL_FILTER_GL_POSITION(gl_Position, geometry);
vec3 offset = edgePadding * positions * outerRadiusPixels;
DECKGL_FILTER_SIZE(offset, geometry);
gl_Position.xy += project_pixel_size_to_clipspace(offset.xy);
} else {
vec3 offset = edgePadding * positions * project_pixel_size(outerRadiusPixels);
DECKGL_FILTER_SIZE(offset, geometry);
gl_Position = project_position_to_clipspace(instancePositions, instancePositions64Low, offset, geometry.position);
DECKGL_FILTER_GL_POSITION(gl_Position, geometry);
}
vFillColor = vec4(instanceFillColors.rgb, instanceFillColors.a * layer.opacity);
DECKGL_FILTER_COLOR(vFillColor, geometry);
vLineColor = vec4(instanceLineColors.rgb, instanceLineColors.a * layer.opacity);
DECKGL_FILTER_COLOR(vLineColor, geometry);
}
`,nc=`#version 300 es
#define SHADER_NAME scatterplot-layer-fragment-shader
precision highp float;
in vec4 vFillColor;
in vec4 vLineColor;
in vec2 unitPosition;
in float innerUnitRadius;
in float outerRadiusPixels;
out vec4 fragColor;
void main(void) {
geometry.uv = unitPosition;
float distToCenter = length(unitPosition) * outerRadiusPixels;
float inCircle = scatterplot.antialiasing ?
smoothedge(distToCenter, outerRadiusPixels) :
step(distToCenter, outerRadiusPixels);
if (inCircle == 0.0) {
discard;
}
if (scatterplot.stroked > 0.5) {
float isLine = scatterplot.antialiasing ?
smoothedge(innerUnitRadius * outerRadiusPixels, distToCenter) :
step(innerUnitRadius * outerRadiusPixels, distToCenter);
if (scatterplot.filled > 0.5) {
fragColor = mix(vFillColor, vLineColor, isLine);
} else {
if (isLine == 0.0) {
discard;
}
fragColor = vec4(vLineColor.rgb, vLineColor.a * isLine);
}
} else if (scatterplot.filled < 0.5) {
discard;
} else {
fragColor = vFillColor;
}
fragColor.a *= inCircle;
DECKGL_FILTER_COLOR(fragColor, geometry);
}
`,oc=`// Main shaders

struct ScatterplotUniforms {
  radiusScale: f32,
  radiusMinPixels: f32,
  radiusMaxPixels: f32,
  lineWidthScale: f32,
  lineWidthMinPixels: f32,
  lineWidthMaxPixels: f32,
  stroked: f32,
  filled: i32,
  antialiasing: i32,
  billboard: i32,
  radiusUnits: i32,
  lineWidthUnits: i32,
};

struct ConstantAttributeUniforms {
 instancePositions: vec3<f32>,
 instancePositions64Low: vec3<f32>,
 instanceRadius: f32,
 instanceLineWidths: f32,
 instanceFillColors: vec4<f32>,
 instanceLineColors: vec4<f32>,
 instancePickingColors: vec3<f32>,

 instancePositionsConstant: i32,
 instancePositions64LowConstant: i32,
 instanceRadiusConstant: i32,
 instanceLineWidthsConstant: i32,
 instanceFillColorsConstant: i32,
 instanceLineColorsConstant: i32,
 instancePickingColorsConstant: i32
};

@group(0) @binding(0) var<uniform> scatterplot: ScatterplotUniforms;

struct ConstantAttributes {
  instancePositions: vec3<f32>,
  instancePositions64Low: vec3<f32>,
  instanceRadius: f32,
  instanceLineWidths: f32,
  instanceFillColors: vec4<f32>,
  instanceLineColors: vec4<f32>,
  instancePickingColors: vec3<f32>
};

const constants = ConstantAttributes(
  vec3<f32>(0.0),
  vec3<f32>(0.0),
  0.0,
  0.0,
  vec4<f32>(0.0, 0.0, 0.0, 1.0),
  vec4<f32>(0.0, 0.0, 0.0, 1.0),
  vec3<f32>(0.0)
);

struct Attributes {
  @builtin(instance_index) instanceIndex : u32,
  @builtin(vertex_index) vertexIndex : u32,
  @location(0) positions: vec3<f32>,
  @location(1) instancePositions: vec3<f32>,
  @location(2) instancePositions64Low: vec3<f32>,
  @location(3) instanceRadius: f32,
  @location(4) instanceLineWidths: f32,
  @location(5) instanceFillColors: vec4<f32>,
  @location(6) instanceLineColors: vec4<f32>,
  @location(7) instancePickingColors: vec3<f32>,
};

struct Varyings {
  @builtin(position) position: vec4<f32>,
  @location(0) vFillColor: vec4<f32>,
  @location(1) vLineColor: vec4<f32>,
  @location(2) unitPosition: vec2<f32>,
  @location(3) innerUnitRadius: f32,
  @location(4) outerRadiusPixels: f32,
  @location(5) pickingColor: vec3<f32>,
};

@vertex
fn vertexMain(attributes: Attributes) -> Varyings {
  var varyings: Varyings;

  // Draw an inline geometry constant array clip space triangle to verify that rendering works.
  // var positions = array<vec2<f32>, 3>(vec2(0.0, 0.5), vec2(-0.5, -0.5), vec2(0.5, -0.5));
  // if (attributes.instanceIndex == 0) {
  //   varyings.position = vec4<f32>(positions[attributes.vertexIndex], 0.0, 1.0);
  //   return varyings;
  // }

  geometry.worldPosition = attributes.instancePositions;

  // Multiply out radius and clamp to limits
  varyings.outerRadiusPixels = clamp(
    project_unit_size_to_pixel(scatterplot.radiusScale * attributes.instanceRadius, scatterplot.radiusUnits),
    scatterplot.radiusMinPixels, scatterplot.radiusMaxPixels
  );

  // Multiply out line width and clamp to limits
  let lineWidthPixels = clamp(
    project_unit_size_to_pixel(scatterplot.lineWidthScale * attributes.instanceLineWidths, scatterplot.lineWidthUnits),
    scatterplot.lineWidthMinPixels, scatterplot.lineWidthMaxPixels
  );

  // outer radius needs to offset by half stroke width
  varyings.outerRadiusPixels += scatterplot.stroked * lineWidthPixels / 2.0;
  // Expand geometry to accommodate edge smoothing
  let edgePadding = select(
    (varyings.outerRadiusPixels + SMOOTH_EDGE_RADIUS) / varyings.outerRadiusPixels,
    1.0,
    scatterplot.antialiasing != 0
  );

  // position on the containing square in [-1, 1] space
  varyings.unitPosition = edgePadding * attributes.positions.xy;
  geometry.uv = varyings.unitPosition;
  geometry.pickingColor = attributes.instancePickingColors;

  varyings.innerUnitRadius = 1.0 - scatterplot.stroked * lineWidthPixels / varyings.outerRadiusPixels;

  if (scatterplot.billboard != 0) {
    varyings.position = project_position_to_clipspace(attributes.instancePositions, attributes.instancePositions64Low, vec3<f32>(0.0)); // TODO , geometry.position);
    // DECKGL_FILTER_GL_POSITION(varyings.position, geometry);
    let offset = attributes.positions; // * edgePadding * varyings.outerRadiusPixels;
    // DECKGL_FILTER_SIZE(offset, geometry);
    let clipPixels = project_pixel_size_to_clipspace(offset.xy);
    varyings.position.x = clipPixels.x;
    varyings.position.y = clipPixels.y;
  } else {
    let offset = edgePadding * attributes.positions * project_pixel_size_float(varyings.outerRadiusPixels);
    // DECKGL_FILTER_SIZE(offset, geometry);
    varyings.position = project_position_to_clipspace(attributes.instancePositions, attributes.instancePositions64Low, offset); // TODO , geometry.position);
    // DECKGL_FILTER_GL_POSITION(varyings.position, geometry);
  }

  // Apply opacity to instance color, or return instance picking color
  varyings.vFillColor = vec4<f32>(attributes.instanceFillColors.rgb, attributes.instanceFillColors.a * layer.opacity);
  // DECKGL_FILTER_COLOR(varyings.vFillColor, geometry);
  varyings.vLineColor = vec4<f32>(attributes.instanceLineColors.rgb, attributes.instanceLineColors.a * layer.opacity);
  // DECKGL_FILTER_COLOR(varyings.vLineColor, geometry);
  varyings.pickingColor = attributes.instancePickingColors;

  return varyings;
}

@fragment
fn fragmentMain(varyings: Varyings) -> @location(0) vec4<f32> {
  // var geometry: Geometry;
  // geometry.uv = unitPosition;

  let distToCenter = length(varyings.unitPosition) * varyings.outerRadiusPixels;
  let inCircle = select(
    smoothedge(distToCenter, varyings.outerRadiusPixels),
    step(distToCenter, varyings.outerRadiusPixels),
    scatterplot.antialiasing != 0
  );

  if (inCircle == 0.0) {
    discard;
  }

  var fragColor: vec4<f32>;

  if (scatterplot.stroked != 0) {
    let isLine = select(
      smoothedge(varyings.innerUnitRadius * varyings.outerRadiusPixels, distToCenter),
      step(varyings.innerUnitRadius * varyings.outerRadiusPixels, distToCenter),
      scatterplot.antialiasing != 0
    );

    if (scatterplot.filled != 0) {
      fragColor = mix(varyings.vFillColor, varyings.vLineColor, isLine);
    } else {
      if (isLine == 0.0) {
        discard;
      }
      fragColor = vec4<f32>(varyings.vLineColor.rgb, varyings.vLineColor.a * isLine);
    }
  } else if (scatterplot.filled == 0) {
    discard;
  } else {
    fragColor = varyings.vFillColor;
  }

  fragColor.a *= inCircle;

  if (picking.isActive > 0.5) {
    if (!picking_isColorValid(varyings.pickingColor)) {
      discard;
    }
    return vec4<f32>(varyings.pickingColor, 1.0);
  }

  if (picking.isHighlightActive > 0.5) {
    let highlightedObjectColor = picking_normalizeColor(picking.highlightedObjectColor);
    if (picking_isColorZero(abs(varyings.pickingColor - highlightedObjectColor))) {
      let highLightAlpha = picking.highlightColor.a;
      let blendedAlpha = highLightAlpha + fragColor.a * (1.0 - highLightAlpha);
      if (blendedAlpha > 0.0) {
        let highLightRatio = highLightAlpha / blendedAlpha;
        fragColor = vec4<f32>(
          mix(fragColor.rgb, picking.highlightColor.rgb, highLightRatio),
          blendedAlpha
        );
      } else {
        fragColor = vec4<f32>(fragColor.rgb, 0.0);
      }
    }
  }

  // Apply premultiplied alpha as required by transparent canvas
  fragColor = deckgl_premultiplied_alpha(fragColor);

  return fragColor;
  // return vec4<f32>(0, 0, 1, 1);
}
`,Hi=[0,0,0,255],sc={radiusUnits:"meters",radiusScale:{type:"number",min:0,value:1},radiusMinPixels:{type:"number",min:0,value:0},radiusMaxPixels:{type:"number",min:0,value:Number.MAX_SAFE_INTEGER},lineWidthUnits:"meters",lineWidthScale:{type:"number",min:0,value:1},lineWidthMinPixels:{type:"number",min:0,value:0},lineWidthMaxPixels:{type:"number",min:0,value:Number.MAX_SAFE_INTEGER},stroked:!1,filled:!0,billboard:!1,antialiasing:!0,getPosition:{type:"accessor",value:n=>n.position},getRadius:{type:"accessor",value:1},getFillColor:{type:"accessor",value:Hi},getLineColor:{type:"accessor",value:Hi},getLineWidth:{type:"accessor",value:1},strokeWidth:{deprecatedFor:"getLineWidth"},outline:{deprecatedFor:"stroked"},getColor:{deprecatedFor:["getFillColor","getLineColor"]}};class ti extends N{getShaders(){return super.getShaders({vs:ic,fs:nc,source:oc,modules:[V,le,W,ec]})}initializeState(){this.getAttributeManager().addInstanced({instancePositions:{size:3,type:"float64",fp64:this.use64bitPositions(),transition:!0,accessor:"getPosition"},instanceRadius:{size:1,transition:!0,accessor:"getRadius",defaultValue:1},instanceFillColors:{size:this.props.colorFormat.length,transition:!0,type:"unorm8",accessor:"getFillColor",defaultValue:[0,0,0,255]},instanceLineColors:{size:this.props.colorFormat.length,transition:!0,type:"unorm8",accessor:"getLineColor",defaultValue:[0,0,0,255]},instanceLineWidths:{size:1,transition:!0,accessor:"getLineWidth",defaultValue:1}})}updateState(t){var e;super.updateState(t),t.changeFlags.extensionsChanged&&((e=this.state.model)==null||e.destroy(),this.state.model=this._getModel(),this.getAttributeManager().invalidateAll())}draw({uniforms:t}){const{radiusUnits:e,radiusScale:i,radiusMinPixels:o,radiusMaxPixels:s,stroked:r,filled:a,billboard:l,antialiasing:c,lineWidthUnits:u,lineWidthScale:f,lineWidthMinPixels:d,lineWidthMaxPixels:h}=this.props,p={stroked:r,filled:a,billboard:l,antialiasing:c,radiusUnits:G[e],radiusScale:i,radiusMinPixels:o,radiusMaxPixels:s,lineWidthUnits:G[u],lineWidthScale:f,lineWidthMinPixels:d,lineWidthMaxPixels:h},g=this.state.model;g.shaderInputs.setProps({scatterplot:p}),g.draw(this.context.renderPass)}_getModel(){const t=[-1,-1,0,1,-1,0,-1,1,0,1,1,0];return new z(this.context.device,{...this.getShaders(),id:this.props.id,bufferLayout:this.getAttributeManager().getBufferLayouts(),geometry:new $({topology:"triangle-strip",attributes:{positions:{size:3,value:new Float32Array(t)}}}),isInstanced:!0})}}ti.defaultProps=sc;ti.layerName="ScatterplotLayer";const ei={CLOCKWISE:1,COUNTER_CLOCKWISE:-1};function ii(n,t,e={}){return rc(n,e)!==t?(lc(n,e),!0):!1}function rc(n,t={}){return Math.sign(ac(n,t))}const Ki={x:0,y:1,z:2};function ac(n,t={}){const{start:e=0,end:i=n.length,plane:o="xy"}=t,s=t.size||2;let r=0;const a=Ki[o[0]],l=Ki[o[1]];for(let c=e,u=i-s;c<i;c+=s)r+=(n[c+a]-n[u+a])*(n[c+l]+n[u+l]),u=c;return r/2}function lc(n,t){const{start:e=0,end:i=n.length,size:o=2}=t,s=(i-e)/o,r=Math.floor(s/2);for(let a=0;a<r;++a){const l=e+a*o,c=e+(s-1-a)*o;for(let u=0;u<o;++u){const f=n[l+u];n[l+u]=n[c+u],n[c+u]=f}}}function j(n,t){const e=t.length,i=n.length;if(i>0){let o=!0;for(let s=0;s<e;s++)if(n[i-e+s]!==t[s]){o=!1;break}if(o)return!1}for(let o=0;o<e;o++)n[i+o]=t[o];return!0}function We(n,t){const e=t.length;for(let i=0;i<e;i++)n[i]=t[i]}function Ct(n,t,e,i,o=[]){const s=i+t*e;for(let r=0;r<e;r++)o[r]=n[s+r];return o}function He(n,t,e,i,o=[]){let s,r;if(e&8)s=(i[3]-n[1])/(t[1]-n[1]),r=3;else if(e&4)s=(i[1]-n[1])/(t[1]-n[1]),r=1;else if(e&2)s=(i[2]-n[0])/(t[0]-n[0]),r=2;else if(e&1)s=(i[0]-n[0])/(t[0]-n[0]),r=0;else return null;for(let a=0;a<n.length;a++)o[a]=(r&1)===a?i[r]:s*(t[a]-n[a])+n[a];return o}function Gt(n,t){let e=0;return n[0]<t[0]?e|=1:n[0]>t[2]&&(e|=2),n[1]<t[1]?e|=4:n[1]>t[3]&&(e|=8),e}function ho(n,t){const{size:e=2,broken:i=!1,gridResolution:o=10,gridOffset:s=[0,0],startIndex:r=0,endIndex:a=n.length}=t||{},l=(a-r)/e;let c=[];const u=[c],f=Ct(n,0,e,r);let d,h;const p=go(f,o,s,[]),g=[];j(c,f);for(let m=1;m<l;m++){for(d=Ct(n,m,e,r,d),h=Gt(d,p);h;){He(f,d,h,p,g);const x=Gt(g,p);x&&(He(f,g,x,p,g),h=x),j(c,g),We(f,g),uc(p,o,h),i&&c.length>e&&(c=[],u.push(c),j(c,f)),h=Gt(d,p)}j(c,d),We(f,d)}return i?u:u[0]}const Yi=0,cc=1;function po(n,t=null,e){if(!n.length)return[];const{size:i=2,gridResolution:o=10,gridOffset:s=[0,0],edgeTypes:r=!1}=e||{},a=[],l=[{pos:n,types:r?new Array(n.length/i).fill(cc):null,holes:t||[]}],c=[[],[]];let u=[];for(;l.length;){const{pos:f,types:d,holes:h}=l.shift();fc(f,i,h[0]||f.length,c),u=go(c[0],o,s,u);const p=Gt(c[1],u);if(p){let g=Zi(f,d,i,0,h[0]||f.length,u,p);const m={pos:g[0].pos,types:g[0].types,holes:[]},x={pos:g[1].pos,types:g[1].types,holes:[]};l.push(m,x);for(let b=0;b<h.length;b++)g=Zi(f,d,i,h[b],h[b+1]||f.length,u,p),g[0]&&(m.holes.push(m.pos.length),m.pos=Rt(m.pos,g[0].pos),r&&(m.types=Rt(m.types,g[0].types))),g[1]&&(x.holes.push(x.pos.length),x.pos=Rt(x.pos,g[1].pos),r&&(x.types=Rt(x.types,g[1].types)))}else{const g={positions:f};r&&(g.edgeTypes=d),h.length&&(g.holeIndices=h),a.push(g)}}return a}function Zi(n,t,e,i,o,s,r){const a=(o-i)/e,l=[],c=[],u=[],f=[],d=[];let h,p,g;const m=Ct(n,a-1,e,i);let x=Math.sign(r&8?m[1]-s[3]:m[0]-s[2]),b=t&&t[a-1],v=0,_=0;for(let C=0;C<a;C++)h=Ct(n,C,e,i,h),p=Math.sign(r&8?h[1]-s[3]:h[0]-s[2]),g=t&&t[i/e+C],p&&x&&x!==p&&(He(m,h,r,s,d),j(l,d)&&u.push(b),j(c,d)&&f.push(b)),p<=0?(j(l,h)&&u.push(g),v-=p):u.length&&(u[u.length-1]=Yi),p>=0?(j(c,h)&&f.push(g),_+=p):f.length&&(f[f.length-1]=Yi),We(m,h),x=p,b=g;return[v?{pos:l,types:t&&u}:null,_?{pos:c,types:t&&f}:null]}function go(n,t,e,i){const o=Math.floor((n[0]-e[0])/t)*t+e[0],s=Math.floor((n[1]-e[1])/t)*t+e[1];return i[0]=o,i[1]=s,i[2]=o+t,i[3]=s+t,i}function uc(n,t,e){e&8?(n[1]+=t,n[3]+=t):e&4?(n[1]-=t,n[3]-=t):e&2?(n[0]+=t,n[2]+=t):e&1&&(n[0]-=t,n[2]-=t)}function fc(n,t,e,i){let o=1/0,s=-1/0,r=1/0,a=-1/0;for(let l=0;l<e;l+=t){const c=n[l],u=n[l+1];o=c<o?c:o,s=c>s?c:s,r=u<r?u:r,a=u>a?u:a}return i[0][0]=o,i[0][1]=r,i[1][0]=s,i[1][1]=a,i}function Rt(n,t){for(let e=0;e<t.length;e++)n.push(t[e]);return n}const dc=85.051129;function hc(n,t){const{size:e=2,startIndex:i=0,endIndex:o=n.length,normalize:s=!0}=t||{},r=n.slice(i,o);mo(r,e,0,o-i);const a=ho(r,{size:e,broken:!0,gridResolution:360,gridOffset:[-180,-180]});if(s)for(const l of a)yo(l,e);return a}function pc(n,t=null,e){const{size:i=2,normalize:o=!0,edgeTypes:s=!1}=e||{};t=t||[];const r=[],a=[];let l=0,c=0;for(let f=0;f<=t.length;f++){const d=t[f]||n.length,h=c,p=gc(n,i,l,d);for(let g=p;g<d;g++)r[c++]=n[g];for(let g=l;g<p;g++)r[c++]=n[g];mo(r,i,h,c),mc(r,i,h,c,e==null?void 0:e.maxLatitude),l=d,a[f]=c}a.pop();const u=po(r,a,{size:i,gridResolution:360,gridOffset:[-180,-180],edgeTypes:s});if(o)for(const f of u)yo(f.positions,i);return u}function gc(n,t,e,i){let o=-1,s=-1;for(let r=e+1;r<i;r+=t){const a=Math.abs(n[r]);a>o&&(o=a,s=r-1)}return s}function mc(n,t,e,i,o=dc){const s=n[e],r=n[i-t];if(Math.abs(s-r)>180){const a=Ct(n,0,t,e);a[0]+=Math.round((r-s)/360)*360,j(n,a),a[1]=Math.sign(a[1])*o,j(n,a),a[0]=s,j(n,a)}}function mo(n,t,e,i){let o=n[0],s;for(let r=e;r<i;r+=t){s=n[r];const a=s-o;(a>180||a<-180)&&(s-=Math.round(a/360)*360),n[r]=o=s}}function yo(n,t){let e;const i=n.length/t;for(let s=0;s<i&&(e=n[s*t],(e+180)%360===0);s++);const o=-Math.round(e/360)*360;if(o!==0)for(let s=0;s<i;s++)n[s*t]+=o}class yc extends ${constructor(t){const{indices:e,attributes:i}=vc(t);super({...t,indices:e,attributes:i})}}function vc(n){const{radius:t,height:e=1,nradial:i=10}=n;let{vertices:o}=n;o&&(T.assert(o.length>=i),o=o.flatMap(h=>[h[0],h[1]]),ii(o,ei.COUNTER_CLOCKWISE));const s=e>0,r=i+1,a=s?r*3+1:i,l=Math.PI*2/i,c=new Uint16Array(s?i*3*2:0),u=new Float32Array(a*3),f=new Float32Array(a*3);let d=0;if(s){for(let h=0;h<r;h++){const p=h*l,g=h%i,m=Math.sin(p),x=Math.cos(p);for(let b=0;b<2;b++)u[d+0]=o?o[g*2]:x*t,u[d+1]=o?o[g*2+1]:m*t,u[d+2]=(1/2-b)*e,f[d+0]=o?o[g*2]:x,f[d+1]=o?o[g*2+1]:m,d+=3}u[d+0]=u[d-3],u[d+1]=u[d-2],u[d+2]=u[d-1],d+=3}for(let h=s?0:1;h<r;h++){const p=Math.floor(h/2)*Math.sign(.5-h%2),g=p*l,m=(p+i)%i,x=Math.sin(g),b=Math.cos(g);u[d+0]=o?o[m*2]:b*t,u[d+1]=o?o[m*2+1]:x*t,u[d+2]=e/2,f[d+2]=1,d+=3}if(s){let h=0;for(let p=0;p<i;p++)c[h++]=p*2+0,c[h++]=p*2+2,c[h++]=p*2+0,c[h++]=p*2+1,c[h++]=p*2+1,c[h++]=p*2+3}return{indices:c,attributes:{POSITION:{size:3,value:u},NORMAL:{size:3,value:f}}}}const qi=`layout(std140) uniform columnUniforms {
  float radius;
  float angle;
  vec2 offset;
  bool extruded;
  bool stroked;
  bool isStroke;
  float coverage;
  float elevationScale;
  float edgeDistance;
  float widthScale;
  float widthMinPixels;
  float widthMaxPixels;
  highp int radiusUnits;
  highp int widthUnits;
} column;
`,_c={name:"column",vs:qi,fs:qi,uniformTypes:{radius:"f32",angle:"f32",offset:"vec2<f32>",extruded:"f32",stroked:"f32",isStroke:"f32",coverage:"f32",elevationScale:"f32",edgeDistance:"f32",widthScale:"f32",widthMinPixels:"f32",widthMaxPixels:"f32",radiusUnits:"i32",widthUnits:"i32"}},xc=`#version 300 es
#define SHADER_NAME column-layer-vertex-shader
in vec3 positions;
in vec3 normals;
in vec3 instancePositions;
in float instanceElevations;
in vec3 instancePositions64Low;
in vec4 instanceFillColors;
in vec4 instanceLineColors;
in float instanceStrokeWidths;
in vec3 instancePickingColors;
out vec4 vColor;
#ifdef FLAT_SHADING
out vec3 cameraPosition;
out vec4 position_commonspace;
#endif
void main(void) {
geometry.worldPosition = instancePositions;
vec4 color = column.isStroke ? instanceLineColors : instanceFillColors;
mat2 rotationMatrix = mat2(cos(column.angle), sin(column.angle), -sin(column.angle), cos(column.angle));
float elevation = 0.0;
float strokeOffsetRatio = 1.0;
if (column.extruded) {
elevation = instanceElevations * (positions.z + 1.0) / 2.0 * column.elevationScale;
} else if (column.stroked) {
float widthPixels = clamp(
project_size_to_pixel(instanceStrokeWidths * column.widthScale, column.widthUnits),
column.widthMinPixels, column.widthMaxPixels) / 2.0;
float halfOffset = project_pixel_size(widthPixels) / project_size(column.edgeDistance * column.coverage * column.radius);
if (column.isStroke) {
strokeOffsetRatio -= sign(positions.z) * halfOffset;
} else {
strokeOffsetRatio -= halfOffset;
}
}
float shouldRender = float(color.a > 0.0 && instanceElevations >= 0.0);
float dotRadius = column.radius * column.coverage * shouldRender;
geometry.pickingColor = instancePickingColors;
vec3 centroidPosition = vec3(instancePositions.xy, instancePositions.z + elevation);
vec3 centroidPosition64Low = instancePositions64Low;
vec2 offset = (rotationMatrix * positions.xy * strokeOffsetRatio + column.offset) * dotRadius;
if (column.radiusUnits == UNIT_METERS) {
offset = project_size(offset);
} else if (column.radiusUnits == UNIT_PIXELS) {
offset = project_pixel_size(offset);
}
vec3 pos = vec3(offset, 0.);
DECKGL_FILTER_SIZE(pos, geometry);
gl_Position = project_position_to_clipspace(centroidPosition, centroidPosition64Low, pos, geometry.position);
geometry.normal = project_normal(vec3(rotationMatrix * normals.xy, normals.z));
DECKGL_FILTER_GL_POSITION(gl_Position, geometry);
if (column.extruded && !column.isStroke) {
#ifdef FLAT_SHADING
cameraPosition = project.cameraPosition;
position_commonspace = geometry.position;
vColor = vec4(color.rgb, color.a * layer.opacity);
#else
vec3 lightColor = lighting_getLightColor(color.rgb, project.cameraPosition, geometry.position.xyz, geometry.normal);
vColor = vec4(lightColor, color.a * layer.opacity);
#endif
} else {
vColor = vec4(color.rgb, color.a * layer.opacity);
}
DECKGL_FILTER_COLOR(vColor, geometry);
}
`,bc=`#version 300 es
#define SHADER_NAME column-layer-fragment-shader
precision highp float;
out vec4 fragColor;
in vec4 vColor;
#ifdef FLAT_SHADING
in vec3 cameraPosition;
in vec4 position_commonspace;
#endif
void main(void) {
fragColor = vColor;
geometry.uv = vec2(0.);
#ifdef FLAT_SHADING
if (column.extruded && !column.isStroke && !bool(picking.isActive)) {
vec3 normal = normalize(cross(dFdx(position_commonspace.xyz), dFdy(position_commonspace.xyz)));
fragColor.rgb = lighting_getLightColor(vColor.rgb, cameraPosition, position_commonspace.xyz, normal);
}
#endif
DECKGL_FILTER_COLOR(fragColor, geometry);
}
`,Jt=[0,0,0,255],Pc={diskResolution:{type:"number",min:4,value:20},vertices:null,radius:{type:"number",min:0,value:1e3},angle:{type:"number",value:0},offset:{type:"array",value:[0,0]},coverage:{type:"number",min:0,max:1,value:1},elevationScale:{type:"number",min:0,value:1},radiusUnits:"meters",lineWidthUnits:"meters",lineWidthScale:1,lineWidthMinPixels:0,lineWidthMaxPixels:Number.MAX_SAFE_INTEGER,extruded:!0,wireframe:!1,filled:!0,stroked:!1,flatShading:!1,getPosition:{type:"accessor",value:n=>n.position},getFillColor:{type:"accessor",value:Jt},getLineColor:{type:"accessor",value:Jt},getLineWidth:{type:"accessor",value:1},getElevation:{type:"accessor",value:1e3},material:!0,getColor:{deprecatedFor:["getFillColor","getLineColor"]}};class ni extends N{getShaders(){const t={},{flatShading:e}=this.props;return e&&(t.FLAT_SHADING=1),super.getShaders({vs:xc,fs:bc,defines:t,modules:[V,e?Fn:ae,W,_c]})}initializeState(){this.getAttributeManager().addInstanced({instancePositions:{size:3,type:"float64",fp64:this.use64bitPositions(),transition:!0,accessor:"getPosition"},instanceElevations:{size:1,transition:!0,accessor:"getElevation"},instanceFillColors:{size:this.props.colorFormat.length,type:"unorm8",transition:!0,accessor:"getFillColor",defaultValue:Jt},instanceLineColors:{size:this.props.colorFormat.length,type:"unorm8",transition:!0,accessor:"getLineColor",defaultValue:Jt},instanceStrokeWidths:{size:1,accessor:"getLineWidth",transition:!0}})}updateState(t){var a;super.updateState(t);const{props:e,oldProps:i,changeFlags:o}=t,s=o.extensionsChanged||e.flatShading!==i.flatShading;s&&((a=this.state.models)==null||a.forEach(l=>l.destroy()),this.setState(this._getModels()),this.getAttributeManager().invalidateAll());const r=this.getNumInstances();this.state.fillModel.setInstanceCount(r),this.state.wireframeModel.setInstanceCount(r),(s||e.diskResolution!==i.diskResolution||e.vertices!==i.vertices||(e.extruded||e.stroked)!==(i.extruded||i.stroked))&&this._updateGeometry(e)}getGeometry(t,e,i){const o=new yc({radius:1,height:i?2:0,vertices:e,nradial:t});let s=0;if(e)for(let r=0;r<t;r++){const a=e[r],l=Math.sqrt(a[0]*a[0]+a[1]*a[1]);s+=l/t}else s=1;return this.setState({edgeDistance:Math.cos(Math.PI/t)*s}),o}_getModels(){const t=this.getShaders(),e=this.getAttributeManager().getBufferLayouts(),i=new z(this.context.device,{...t,id:`${this.props.id}-fill`,bufferLayout:e,isInstanced:!0}),o=new z(this.context.device,{...t,id:`${this.props.id}-wireframe`,bufferLayout:e,isInstanced:!0});return{fillModel:i,wireframeModel:o,models:[o,i]}}_updateGeometry({diskResolution:t,vertices:e,extruded:i,stroked:o}){const s=this.getGeometry(t,e,i||o);this.setState({fillVertexCount:s.attributes.POSITION.value.length/3});const r=this.state.fillModel,a=this.state.wireframeModel;r.setGeometry(s),r.setTopology("triangle-strip"),r.setIndexBuffer(null),a.setGeometry(s),a.setTopology("line-list")}draw({uniforms:t}){const{lineWidthUnits:e,lineWidthScale:i,lineWidthMinPixels:o,lineWidthMaxPixels:s,radiusUnits:r,elevationScale:a,extruded:l,filled:c,stroked:u,wireframe:f,offset:d,coverage:h,radius:p,angle:g}=this.props,m=this.state.fillModel,x=this.state.wireframeModel,{fillVertexCount:b,edgeDistance:v}=this.state,_={radius:p,angle:g/180*Math.PI,offset:d,extruded:l,stroked:u,coverage:h,elevationScale:a,edgeDistance:v,radiusUnits:G[r],widthUnits:G[e],widthScale:i,widthMinPixels:o,widthMaxPixels:s};l&&f&&(x.shaderInputs.setProps({column:{..._,isStroke:!0}}),x.draw(this.context.renderPass)),c&&(m.setVertexCount(b),m.shaderInputs.setProps({column:{..._,isStroke:!1}}),m.draw(this.context.renderPass)),!l&&u&&(m.setVertexCount(b*2/3),m.shaderInputs.setProps({column:{..._,isStroke:!0}}),m.draw(this.context.renderPass))}}ni.layerName="ColumnLayer";ni.defaultProps=Pc;const Cc={cellSize:{type:"number",min:0,value:1e3},offset:{type:"array",value:[1,1]}};class vo extends ni{_updateGeometry(){const t=new Rr;this.state.fillModel.setGeometry(t)}draw({uniforms:t}){const{elevationScale:e,extruded:i,offset:o,coverage:s,cellSize:r,angle:a,radiusUnits:l}=this.props,c=this.state.fillModel,u={radius:r/2,radiusUnits:G[l],angle:a,offset:o,extruded:i,stroked:!1,coverage:s,elevationScale:e,edgeDistance:1,isStroke:!1,widthUnits:0,widthScale:0,widthMinPixels:0,widthMaxPixels:0};c.shaderInputs.setProps({column:u}),c.draw(this.context.renderPass)}}vo.layerName="GridCellLayer";vo.defaultProps=Cc;function Lc(n,t,e,i){let o;if(Array.isArray(n[0])){const s=n.length*t;o=new Array(s);for(let r=0;r<n.length;r++)for(let a=0;a<t;a++)o[r*t+a]=n[r][a]||0}else o=n;return e?ho(o,{size:t,gridResolution:e}):i?hc(o,{size:t}):o}const wc=1,Ac=2,Le=4;class Sc extends no{constructor(t){super({...t,attributes:{positions:{size:3,padding:18,initialize:!0,type:t.fp64?Float64Array:Float32Array},segmentTypes:{size:1,type:Uint8ClampedArray}}})}get(t){return this.attributes[t]}getGeometryFromBuffer(t){return this.normalize?super.getGeometryFromBuffer(t):null}normalizeGeometry(t){return this.normalize?Lc(t,this.positionSize,this.opts.resolution,this.opts.wrapLongitude):t}getGeometrySize(t){if(Xi(t)){let i=0;for(const o of t)i+=this.getGeometrySize(o);return i}const e=this.getPathLength(t);return e<2?0:this.isClosed(t)?e<3?0:e+2:e}updateGeometryAttributes(t,e){if(e.geometrySize!==0)if(t&&Xi(t))for(const i of t){const o=this.getGeometrySize(i);e.geometrySize=o,this.updateGeometryAttributes(i,e),e.vertexStart+=o}else this._updateSegmentTypes(t,e),this._updatePositions(t,e)}_updateSegmentTypes(t,e){const i=this.attributes.segmentTypes,o=t?this.isClosed(t):!1,{vertexStart:s,geometrySize:r}=e;i.fill(0,s,s+r),o?(i[s]=Le,i[s+r-2]=Le):(i[s]+=wc,i[s+r-2]+=Ac),i[s+r-1]=Le}_updatePositions(t,e){const{positions:i}=this.attributes;if(!i||!t)return;const{vertexStart:o,geometrySize:s}=e,r=new Array(3);for(let a=o,l=0;l<s;a++,l++)this.getPointOnPath(t,l,r),i[a*3]=r[0],i[a*3+1]=r[1],i[a*3+2]=r[2]}getPathLength(t){return t.length/this.positionSize}getPointOnPath(t,e,i=[]){const{positionSize:o}=this;e*o>=t.length&&(e+=1-t.length/o);const s=e*o;return i[0]=t[s],i[1]=t[s+1],i[2]=o===3&&t[s+2]||0,i}isClosed(t){if(!this.normalize)return!!this.opts.loop;const{positionSize:e}=this,i=t.length-e;return t[0]===t[i]&&t[1]===t[i+1]&&(e===2||t[2]===t[i+2])}}function Xi(n){return Array.isArray(n[0])}const Ji=`layout(std140) uniform pathUniforms {
  float widthScale;
  float widthMinPixels;
  float widthMaxPixels;
  float jointType;
  float capType;
  float miterLimit;
  bool billboard;
  highp int widthUnits;
} path;
`,Tc={name:"path",vs:Ji,fs:Ji,uniformTypes:{widthScale:"f32",widthMinPixels:"f32",widthMaxPixels:"f32",jointType:"f32",capType:"f32",miterLimit:"f32",billboard:"f32",widthUnits:"i32"}},Ec=`#version 300 es
#define SHADER_NAME path-layer-vertex-shader
in vec2 positions;
in float instanceTypes;
in vec3 instanceStartPositions;
in vec3 instanceEndPositions;
in vec3 instanceLeftPositions;
in vec3 instanceRightPositions;
in vec3 instanceLeftPositions64Low;
in vec3 instanceStartPositions64Low;
in vec3 instanceEndPositions64Low;
in vec3 instanceRightPositions64Low;
in float instanceStrokeWidths;
in vec4 instanceColors;
in vec3 instancePickingColors;
uniform float opacity;
out vec4 vColor;
out vec2 vCornerOffset;
out float vMiterLength;
out vec2 vPathPosition;
out float vPathLength;
out float vJointType;
const float EPSILON = 0.001;
const vec3 ZERO_OFFSET = vec3(0.0);
float flipIfTrue(bool flag) {
return -(float(flag) * 2. - 1.);
}
vec3 getLineJoinOffset(
vec3 prevPoint, vec3 currPoint, vec3 nextPoint,
vec2 width
) {
bool isEnd = positions.x > 0.0;
float sideOfPath = positions.y;
float isJoint = float(sideOfPath == 0.0);
vec3 deltaA3 = (currPoint - prevPoint);
vec3 deltaB3 = (nextPoint - currPoint);
mat3 rotationMatrix;
bool needsRotation = !path.billboard && project_needs_rotation(currPoint, rotationMatrix);
if (needsRotation) {
deltaA3 = deltaA3 * rotationMatrix;
deltaB3 = deltaB3 * rotationMatrix;
}
vec2 deltaA = deltaA3.xy / width;
vec2 deltaB = deltaB3.xy / width;
float lenA = length(deltaA);
float lenB = length(deltaB);
vec2 dirA = lenA > 0. ? normalize(deltaA) : vec2(0.0, 0.0);
vec2 dirB = lenB > 0. ? normalize(deltaB) : vec2(0.0, 0.0);
vec2 perpA = vec2(-dirA.y, dirA.x);
vec2 perpB = vec2(-dirB.y, dirB.x);
vec2 tangent = dirA + dirB;
tangent = length(tangent) > 0. ? normalize(tangent) : perpA;
vec2 miterVec = vec2(-tangent.y, tangent.x);
vec2 dir = isEnd ? dirA : dirB;
vec2 perp = isEnd ? perpA : perpB;
float L = isEnd ? lenA : lenB;
float sinHalfA = abs(dot(miterVec, perp));
float cosHalfA = abs(dot(dirA, miterVec));
float turnDirection = flipIfTrue(dirA.x * dirB.y >= dirA.y * dirB.x);
float cornerPosition = sideOfPath * turnDirection;
float miterSize = 1.0 / max(sinHalfA, EPSILON);
miterSize = mix(
min(miterSize, max(lenA, lenB) / max(cosHalfA, EPSILON)),
miterSize,
step(0.0, cornerPosition)
);
vec2 offsetVec = mix(miterVec * miterSize, perp, step(0.5, cornerPosition))
* (sideOfPath + isJoint * turnDirection);
bool isStartCap = lenA == 0.0 || (!isEnd && (instanceTypes == 1.0 || instanceTypes == 3.0));
bool isEndCap = lenB == 0.0 || (isEnd && (instanceTypes == 2.0 || instanceTypes == 3.0));
bool isCap = isStartCap || isEndCap;
if (isCap) {
offsetVec = mix(perp * sideOfPath, dir * path.capType * 4.0 * flipIfTrue(isStartCap), isJoint);
vJointType = path.capType;
} else {
vJointType = path.jointType;
}
vPathLength = L;
vCornerOffset = offsetVec;
vMiterLength = dot(vCornerOffset, miterVec * turnDirection);
vMiterLength = isCap ? isJoint : vMiterLength;
vec2 offsetFromStartOfPath = vCornerOffset + deltaA * float(isEnd);
vPathPosition = vec2(
dot(offsetFromStartOfPath, perp),
dot(offsetFromStartOfPath, dir)
);
geometry.uv = vPathPosition;
float isValid = step(instanceTypes, 3.5);
vec3 offset = vec3(offsetVec * width * isValid, 0.0);
if (needsRotation) {
offset = rotationMatrix * offset;
}
return offset;
}
void clipLine(inout vec4 position, vec4 refPosition) {
if (position.w < EPSILON) {
float r = (EPSILON - refPosition.w) / (position.w - refPosition.w);
position = refPosition + (position - refPosition) * r;
}
}
void main() {
geometry.pickingColor = instancePickingColors;
vColor = vec4(instanceColors.rgb, instanceColors.a * layer.opacity);
float isEnd = positions.x;
vec3 prevPosition = mix(instanceLeftPositions, instanceStartPositions, isEnd);
vec3 prevPosition64Low = mix(instanceLeftPositions64Low, instanceStartPositions64Low, isEnd);
vec3 currPosition = mix(instanceStartPositions, instanceEndPositions, isEnd);
vec3 currPosition64Low = mix(instanceStartPositions64Low, instanceEndPositions64Low, isEnd);
vec3 nextPosition = mix(instanceEndPositions, instanceRightPositions, isEnd);
vec3 nextPosition64Low = mix(instanceEndPositions64Low, instanceRightPositions64Low, isEnd);
geometry.worldPosition = currPosition;
vec2 widthPixels = vec2(clamp(
project_size_to_pixel(instanceStrokeWidths * path.widthScale, path.widthUnits),
path.widthMinPixels, path.widthMaxPixels) / 2.0);
vec3 width;
if (path.billboard) {
vec4 prevPositionScreen = project_position_to_clipspace(prevPosition, prevPosition64Low, ZERO_OFFSET);
vec4 currPositionScreen = project_position_to_clipspace(currPosition, currPosition64Low, ZERO_OFFSET, geometry.position);
vec4 nextPositionScreen = project_position_to_clipspace(nextPosition, nextPosition64Low, ZERO_OFFSET);
clipLine(prevPositionScreen, currPositionScreen);
clipLine(nextPositionScreen, currPositionScreen);
clipLine(currPositionScreen, mix(nextPositionScreen, prevPositionScreen, isEnd));
width = vec3(widthPixels, 0.0);
DECKGL_FILTER_SIZE(width, geometry);
vec3 offset = getLineJoinOffset(
prevPositionScreen.xyz / prevPositionScreen.w,
currPositionScreen.xyz / currPositionScreen.w,
nextPositionScreen.xyz / nextPositionScreen.w,
project_pixel_size_to_clipspace(width.xy)
);
DECKGL_FILTER_GL_POSITION(currPositionScreen, geometry);
gl_Position = vec4(currPositionScreen.xyz + offset * currPositionScreen.w, currPositionScreen.w);
} else {
prevPosition = project_position(prevPosition, prevPosition64Low);
currPosition = project_position(currPosition, currPosition64Low);
nextPosition = project_position(nextPosition, nextPosition64Low);
width = vec3(project_pixel_size(widthPixels), 0.0);
DECKGL_FILTER_SIZE(width, geometry);
vec3 offset = getLineJoinOffset(prevPosition, currPosition, nextPosition, width.xy);
geometry.position = vec4(currPosition + offset, 1.0);
gl_Position = project_common_position_to_clipspace(geometry.position);
DECKGL_FILTER_GL_POSITION(gl_Position, geometry);
}
DECKGL_FILTER_COLOR(vColor, geometry);
}
`,Ic=`#version 300 es
#define SHADER_NAME path-layer-fragment-shader
precision highp float;
in vec4 vColor;
in vec2 vCornerOffset;
in float vMiterLength;
in vec2 vPathPosition;
in float vPathLength;
in float vJointType;
out vec4 fragColor;
void main(void) {
geometry.uv = vPathPosition;
if (vPathPosition.y < 0.0 || vPathPosition.y > vPathLength) {
if (vJointType > 0.5 && length(vCornerOffset) > 1.0) {
discard;
}
if (vJointType < 0.5 && vMiterLength > path.miterLimit + 1.0) {
discard;
}
}
fragColor = vColor;
DECKGL_FILTER_COLOR(fragColor, geometry);
}
`,_o=[0,0,0,255],Oc={widthUnits:"meters",widthScale:{type:"number",min:0,value:1},widthMinPixels:{type:"number",min:0,value:0},widthMaxPixels:{type:"number",min:0,value:Number.MAX_SAFE_INTEGER},jointRounded:!1,capRounded:!1,miterLimit:{type:"number",min:0,value:4},billboard:!1,_pathType:null,getPath:{type:"accessor",value:n=>n.path},getColor:{type:"accessor",value:_o},getWidth:{type:"accessor",value:1},rounded:{deprecatedFor:["jointRounded","capRounded"]}},we={enter:(n,t)=>t.length?t.subarray(t.length-n.length):n};class de extends N{getShaders(){return super.getShaders({vs:Ec,fs:Ic,modules:[V,W,Tc]})}get wrapLongitude(){return!1}getBounds(){var t;return(t=this.getAttributeManager())==null?void 0:t.getBounds(["vertexPositions"])}initializeState(){this.getAttributeManager().addInstanced({vertexPositions:{size:3,vertexOffset:1,type:"float64",fp64:this.use64bitPositions(),transition:we,accessor:"getPath",update:this.calculatePositions,noAlloc:!0,shaderAttributes:{instanceLeftPositions:{vertexOffset:0},instanceStartPositions:{vertexOffset:1},instanceEndPositions:{vertexOffset:2},instanceRightPositions:{vertexOffset:3}}},instanceTypes:{size:1,type:"uint8",update:this.calculateSegmentTypes,noAlloc:!0},instanceStrokeWidths:{size:1,accessor:"getWidth",transition:we,defaultValue:1},instanceColors:{size:this.props.colorFormat.length,type:"unorm8",accessor:"getColor",transition:we,defaultValue:_o},instancePickingColors:{size:4,type:"uint8",accessor:(i,{index:o,target:s})=>this.encodePickingColor(i&&i.__source?i.__source.index:o,s)}}),this.setState({pathTesselator:new Sc({fp64:this.use64bitPositions()})})}updateState(t){var r;super.updateState(t);const{props:e,changeFlags:i}=t,o=this.getAttributeManager();if(i.dataChanged||i.updateTriggersChanged&&(i.updateTriggersChanged.all||i.updateTriggersChanged.getPath)){const{pathTesselator:a}=this.state,l=e.data.attributes||{};a.updateGeometry({data:e.data,geometryBuffer:l.getPath,buffers:l,normalize:!e._pathType,loop:e._pathType==="loop",getGeometry:e.getPath,positionFormat:e.positionFormat,wrapLongitude:e.wrapLongitude,resolution:this.context.viewport.resolution,dataChanged:i.dataChanged}),this.setState({numInstances:a.instanceCount,startIndices:a.vertexStarts}),i.dataChanged||o.invalidateAll()}i.extensionsChanged&&((r=this.state.model)==null||r.destroy(),this.state.model=this._getModel(),o.invalidateAll())}getPickingInfo(t){const e=super.getPickingInfo(t),{index:i}=e,o=this.props.data;return o[0]&&o[0].__source&&(e.object=o.find(s=>s.__source.index===i)),e}disablePickingIndex(t){const e=this.props.data;if(e[0]&&e[0].__source)for(let i=0;i<e.length;i++)e[i].__source.index===t&&this._disablePickingIndex(i);else super.disablePickingIndex(t)}draw({uniforms:t}){const{jointRounded:e,capRounded:i,billboard:o,miterLimit:s,widthUnits:r,widthScale:a,widthMinPixels:l,widthMaxPixels:c}=this.props,u=this.state.model,f={jointType:Number(e),capType:Number(i),billboard:o,widthUnits:G[r],widthScale:a,miterLimit:s,widthMinPixels:l,widthMaxPixels:c};u.shaderInputs.setProps({path:f}),u.draw(this.context.renderPass)}_getModel(){const t=[0,1,2,1,4,2,1,3,4,3,5,4],e=[0,0,0,-1,0,1,1,-1,1,1,1,0];return new z(this.context.device,{...this.getShaders(),id:this.props.id,bufferLayout:this.getAttributeManager().getBufferLayouts(),geometry:new $({topology:"triangle-list",attributes:{indices:new Uint16Array(t),positions:{value:new Float32Array(e),size:2}}}),isInstanced:!0})}calculatePositions(t){const{pathTesselator:e}=this.state;t.startIndices=e.vertexStarts,t.value=e.get("positions")}calculateSegmentTypes(t){const{pathTesselator:e}=this.state;t.startIndices=e.vertexStarts,t.value=e.get("segmentTypes")}}de.defaultProps=Oc;de.layerName="PathLayer";var oi={exports:{}};oi.exports=he;oi.exports.default=he;function he(n,t,e){e=e||2;var i=t&&t.length,o=i?t[0]*e:n.length,s=xo(n,0,o,e,!0),r=[];if(!s||s.next===s.prev)return r;var a,l,c,u,f,d,h;if(i&&(s=kc(n,t,s,e)),n.length>80*e){a=c=n[0],l=u=n[1];for(var p=e;p<o;p+=e)f=n[p],d=n[p+1],f<a&&(a=f),d<l&&(l=d),f>c&&(c=f),d>u&&(u=d);h=Math.max(c-a,u-l),h=h!==0?32767/h:0}return Lt(s,r,e,a,l,h,0),r}function xo(n,t,e,i,o){var s,r;if(o===Ze(n,t,e,i)>0)for(s=t;s<e;s+=i)r=Qi(s,n[s],n[s+1],r);else for(s=e-i;s>=t;s-=i)r=Qi(s,n[s],n[s+1],r);return r&&pe(r,r.next)&&(At(r),r=r.next),r}function nt(n,t){if(!n)return n;t||(t=n);var e=n,i;do if(i=!1,!e.steiner&&(pe(e,e.next)||A(e.prev,e,e.next)===0)){if(At(e),e=t=e.prev,e===e.next)break;i=!0}else e=e.next;while(i||e!==t);return t}function Lt(n,t,e,i,o,s,r){if(n){!r&&s&&jc(n,i,o,s);for(var a=n,l,c;n.prev!==n.next;){if(l=n.prev,c=n.next,s?Rc(n,i,o,s):Mc(n)){t.push(l.i/e|0),t.push(n.i/e|0),t.push(c.i/e|0),At(n),n=c.next,a=c.next;continue}if(n=c,n===a){r?r===1?(n=zc(nt(n),t,e),Lt(n,t,e,i,o,s,2)):r===2&&Fc(n,t,e,i,o,s):Lt(nt(n),t,e,i,o,s,1);break}}}}function Mc(n){var t=n.prev,e=n,i=n.next;if(A(t,e,i)>=0)return!1;for(var o=t.x,s=e.x,r=i.x,a=t.y,l=e.y,c=i.y,u=o<s?o<r?o:r:s<r?s:r,f=a<l?a<c?a:c:l<c?l:c,d=o>s?o>r?o:r:s>r?s:r,h=a>l?a>c?a:c:l>c?l:c,p=i.next;p!==t;){if(p.x>=u&&p.x<=d&&p.y>=f&&p.y<=h&&st(o,a,s,l,r,c,p.x,p.y)&&A(p.prev,p,p.next)>=0)return!1;p=p.next}return!0}function Rc(n,t,e,i){var o=n.prev,s=n,r=n.next;if(A(o,s,r)>=0)return!1;for(var a=o.x,l=s.x,c=r.x,u=o.y,f=s.y,d=r.y,h=a<l?a<c?a:c:l<c?l:c,p=u<f?u<d?u:d:f<d?f:d,g=a>l?a>c?a:c:l>c?l:c,m=u>f?u>d?u:d:f>d?f:d,x=Ke(h,p,t,e,i),b=Ke(g,m,t,e,i),v=n.prevZ,_=n.nextZ;v&&v.z>=x&&_&&_.z<=b;){if(v.x>=h&&v.x<=g&&v.y>=p&&v.y<=m&&v!==o&&v!==r&&st(a,u,l,f,c,d,v.x,v.y)&&A(v.prev,v,v.next)>=0||(v=v.prevZ,_.x>=h&&_.x<=g&&_.y>=p&&_.y<=m&&_!==o&&_!==r&&st(a,u,l,f,c,d,_.x,_.y)&&A(_.prev,_,_.next)>=0))return!1;_=_.nextZ}for(;v&&v.z>=x;){if(v.x>=h&&v.x<=g&&v.y>=p&&v.y<=m&&v!==o&&v!==r&&st(a,u,l,f,c,d,v.x,v.y)&&A(v.prev,v,v.next)>=0)return!1;v=v.prevZ}for(;_&&_.z<=b;){if(_.x>=h&&_.x<=g&&_.y>=p&&_.y<=m&&_!==o&&_!==r&&st(a,u,l,f,c,d,_.x,_.y)&&A(_.prev,_,_.next)>=0)return!1;_=_.nextZ}return!0}function zc(n,t,e){var i=n;do{var o=i.prev,s=i.next.next;!pe(o,s)&&bo(o,i,i.next,s)&&wt(o,s)&&wt(s,o)&&(t.push(o.i/e|0),t.push(i.i/e|0),t.push(s.i/e|0),At(i),At(i.next),i=n=s),i=i.next}while(i!==n);return nt(i)}function Fc(n,t,e,i,o,s){var r=n;do{for(var a=r.next.next;a!==r.prev;){if(r.i!==a.i&&Vc(r,a)){var l=Po(r,a);r=nt(r,r.next),l=nt(l,l.next),Lt(r,t,e,i,o,s,0),Lt(l,t,e,i,o,s,0);return}a=a.next}r=r.next}while(r!==n)}function kc(n,t,e,i){var o=[],s,r,a,l,c;for(s=0,r=t.length;s<r;s++)a=t[s]*i,l=s<r-1?t[s+1]*i:n.length,c=xo(n,a,l,i,!1),c===c.next&&(c.steiner=!0),o.push($c(c));for(o.sort(Bc),s=0;s<o.length;s++)e=Nc(o[s],e);return e}function Bc(n,t){return n.x-t.x}function Nc(n,t){var e=Uc(n,t);if(!e)return t;var i=Po(e,n);return nt(i,i.next),nt(e,e.next)}function Uc(n,t){var e=t,i=n.x,o=n.y,s=-1/0,r;do{if(o<=e.y&&o>=e.next.y&&e.next.y!==e.y){var a=e.x+(o-e.y)*(e.next.x-e.x)/(e.next.y-e.y);if(a<=i&&a>s&&(s=a,r=e.x<e.next.x?e:e.next,a===i))return r}e=e.next}while(e!==t);if(!r)return null;var l=r,c=r.x,u=r.y,f=1/0,d;e=r;do i>=e.x&&e.x>=c&&i!==e.x&&st(o<u?i:s,o,c,u,o<u?s:i,o,e.x,e.y)&&(d=Math.abs(o-e.y)/(i-e.x),wt(e,n)&&(d<f||d===f&&(e.x>r.x||e.x===r.x&&Dc(r,e)))&&(r=e,f=d)),e=e.next;while(e!==l);return r}function Dc(n,t){return A(n.prev,n,t.prev)<0&&A(t.next,n,n.next)<0}function jc(n,t,e,i){var o=n;do o.z===0&&(o.z=Ke(o.x,o.y,t,e,i)),o.prevZ=o.prev,o.nextZ=o.next,o=o.next;while(o!==n);o.prevZ.nextZ=null,o.prevZ=null,Gc(o)}function Gc(n){var t,e,i,o,s,r,a,l,c=1;do{for(e=n,n=null,s=null,r=0;e;){for(r++,i=e,a=0,t=0;t<c&&(a++,i=i.nextZ,!!i);t++);for(l=c;a>0||l>0&&i;)a!==0&&(l===0||!i||e.z<=i.z)?(o=e,e=e.nextZ,a--):(o=i,i=i.nextZ,l--),s?s.nextZ=o:n=o,o.prevZ=s,s=o;e=i}s.nextZ=null,c*=2}while(r>1);return n}function Ke(n,t,e,i,o){return n=(n-e)*o|0,t=(t-i)*o|0,n=(n|n<<8)&16711935,n=(n|n<<4)&252645135,n=(n|n<<2)&858993459,n=(n|n<<1)&1431655765,t=(t|t<<8)&16711935,t=(t|t<<4)&252645135,t=(t|t<<2)&858993459,t=(t|t<<1)&1431655765,n|t<<1}function $c(n){var t=n,e=n;do(t.x<e.x||t.x===e.x&&t.y<e.y)&&(e=t),t=t.next;while(t!==n);return e}function st(n,t,e,i,o,s,r,a){return(o-r)*(t-a)>=(n-r)*(s-a)&&(n-r)*(i-a)>=(e-r)*(t-a)&&(e-r)*(s-a)>=(o-r)*(i-a)}function Vc(n,t){return n.next.i!==t.i&&n.prev.i!==t.i&&!Wc(n,t)&&(wt(n,t)&&wt(t,n)&&Hc(n,t)&&(A(n.prev,n,t.prev)||A(n,t.prev,t))||pe(n,t)&&A(n.prev,n,n.next)>0&&A(t.prev,t,t.next)>0)}function A(n,t,e){return(t.y-n.y)*(e.x-t.x)-(t.x-n.x)*(e.y-t.y)}function pe(n,t){return n.x===t.x&&n.y===t.y}function bo(n,t,e,i){var o=Ft(A(n,t,e)),s=Ft(A(n,t,i)),r=Ft(A(e,i,n)),a=Ft(A(e,i,t));return!!(o!==s&&r!==a||o===0&&zt(n,e,t)||s===0&&zt(n,i,t)||r===0&&zt(e,n,i)||a===0&&zt(e,t,i))}function zt(n,t,e){return t.x<=Math.max(n.x,e.x)&&t.x>=Math.min(n.x,e.x)&&t.y<=Math.max(n.y,e.y)&&t.y>=Math.min(n.y,e.y)}function Ft(n){return n>0?1:n<0?-1:0}function Wc(n,t){var e=n;do{if(e.i!==n.i&&e.next.i!==n.i&&e.i!==t.i&&e.next.i!==t.i&&bo(e,e.next,n,t))return!0;e=e.next}while(e!==n);return!1}function wt(n,t){return A(n.prev,n,n.next)<0?A(n,t,n.next)>=0&&A(n,n.prev,t)>=0:A(n,t,n.prev)<0||A(n,n.next,t)<0}function Hc(n,t){var e=n,i=!1,o=(n.x+t.x)/2,s=(n.y+t.y)/2;do e.y>s!=e.next.y>s&&e.next.y!==e.y&&o<(e.next.x-e.x)*(s-e.y)/(e.next.y-e.y)+e.x&&(i=!i),e=e.next;while(e!==n);return i}function Po(n,t){var e=new Ye(n.i,n.x,n.y),i=new Ye(t.i,t.x,t.y),o=n.next,s=t.prev;return n.next=t,t.prev=n,e.next=o,o.prev=e,i.next=e,e.prev=i,s.next=i,i.prev=s,i}function Qi(n,t,e,i){var o=new Ye(n,t,e);return i?(o.next=i.next,o.prev=i,i.next.prev=o,i.next=o):(o.prev=o,o.next=o),o}function At(n){n.next.prev=n.prev,n.prev.next=n.next,n.prevZ&&(n.prevZ.nextZ=n.nextZ),n.nextZ&&(n.nextZ.prevZ=n.prevZ)}function Ye(n,t,e){this.i=n,this.x=t,this.y=e,this.prev=null,this.next=null,this.z=0,this.prevZ=null,this.nextZ=null,this.steiner=!1}he.deviation=function(n,t,e,i){var o=t&&t.length,s=o?t[0]*e:n.length,r=Math.abs(Ze(n,0,s,e));if(o)for(var a=0,l=t.length;a<l;a++){var c=t[a]*e,u=a<l-1?t[a+1]*e:n.length;r-=Math.abs(Ze(n,c,u,e))}var f=0;for(a=0;a<i.length;a+=3){var d=i[a]*e,h=i[a+1]*e,p=i[a+2]*e;f+=Math.abs((n[d]-n[p])*(n[h+1]-n[d+1])-(n[d]-n[h])*(n[p+1]-n[d+1]))}return r===0&&f===0?0:Math.abs((f-r)/r)};function Ze(n,t,e,i){for(var o=0,s=t,r=e-i;s<e;s+=i)o+=(n[r]-n[s])*(n[s+1]+n[r+1]),r=s;return o}he.flatten=function(n){for(var t=n[0][0].length,e={vertices:[],holes:[],dimensions:t},i=0,o=0;o<n.length;o++){for(var s=0;s<n[o].length;s++)for(var r=0;r<t;r++)e.vertices.push(n[o][s][r]);o>0&&(i+=n[o-1].length,e.holes.push(i))}return e};var Kc=oi.exports;const Yc=cs(Kc),kt=ei.CLOCKWISE,tn=ei.COUNTER_CLOCKWISE,X={};function Zc(n){if(n=n&&n.positions||n,!Array.isArray(n)&&!ArrayBuffer.isView(n))throw new Error("invalid polygon")}function mt(n){return"positions"in n?n.positions:n}function $t(n){return"holeIndices"in n?n.holeIndices:null}function qc(n){return Array.isArray(n[0])}function Xc(n){return n.length>=1&&n[0].length>=2&&Number.isFinite(n[0][0])}function Jc(n){const t=n[0],e=n[n.length-1];return t[0]===e[0]&&t[1]===e[1]&&t[2]===e[2]}function Qc(n,t,e,i){for(let o=0;o<t;o++)if(n[e+o]!==n[i-t+o])return!1;return!0}function en(n,t,e,i,o){let s=t;const r=e.length;for(let a=0;a<r;a++)for(let l=0;l<i;l++)n[s++]=e[a][l]||0;if(!Jc(e))for(let a=0;a<i;a++)n[s++]=e[0][a]||0;return X.start=t,X.end=s,X.size=i,ii(n,o,X),s}function nn(n,t,e,i,o=0,s,r){s=s||e.length;const a=s-o;if(a<=0)return t;let l=t;for(let c=0;c<a;c++)n[l++]=e[o+c];if(!Qc(e,i,o,s))for(let c=0;c<i;c++)n[l++]=e[o+c];return X.start=t,X.end=l,X.size=i,ii(n,r,X),l}function Co(n,t){Zc(n);const e=[],i=[];if("positions"in n){const{positions:o,holeIndices:s}=n;if(s){let r=0;for(let a=0;a<=s.length;a++)r=nn(e,r,o,t,s[a-1],s[a],a===0?kt:tn),i.push(r);return i.pop(),{positions:e,holeIndices:i}}n=o}if(!qc(n))return nn(e,0,n,t,0,e.length,kt),e;if(!Xc(n)){let o=0;for(const[s,r]of n.entries())o=en(e,o,r,t,s===0?kt:tn),i.push(o);return i.pop(),{positions:e,holeIndices:i}}return en(e,0,n,t,kt),e}function Ae(n,t,e){const i=n.length/3;let o=0;for(let s=0;s<i;s++){const r=(s+1)%i;o+=n[s*3+t]*n[r*3+e],o-=n[r*3+t]*n[s*3+e]}return Math.abs(o/2)}function on(n,t,e,i){const o=n.length/3;for(let s=0;s<o;s++){const r=s*3,a=n[r+0],l=n[r+1],c=n[r+2];n[r+t]=a,n[r+e]=l,n[r+i]=c}}function tu(n,t,e,i){let o=$t(n);o&&(o=o.map(a=>a/t));let s=mt(n);const r=i&&t===3;if(e){const a=s.length;s=s.slice();const l=[];for(let c=0;c<a;c+=t){l[0]=s[c],l[1]=s[c+1],r&&(l[2]=s[c+2]);const u=e(l);s[c]=u[0],s[c+1]=u[1],r&&(s[c+2]=u[2])}}if(r){const a=Ae(s,0,1),l=Ae(s,0,2),c=Ae(s,1,2);if(!a&&!l&&!c)return[];a>l&&a>c||(l>c?(e||(s=s.slice()),on(s,0,2,1)):(e||(s=s.slice()),on(s,2,0,1)))}return Yc(s,o,t)}class eu extends no{constructor(t){const{fp64:e,IndexType:i=Uint32Array}=t;super({...t,attributes:{positions:{size:3,type:e?Float64Array:Float32Array},vertexValid:{type:Uint16Array,size:1},indices:{type:i,size:1}}})}get(t){const{attributes:e}=this;return t==="indices"?e.indices&&e.indices.subarray(0,this.vertexCount):e[t]}updateGeometry(t){super.updateGeometry(t);const e=this.buffers.indices;if(e)this.vertexCount=(e.value||e).length;else if(this.data&&!this.getGeometry)throw new Error("missing indices buffer")}normalizeGeometry(t){if(this.normalize){const e=Co(t,this.positionSize);return this.opts.resolution?po(mt(e),$t(e),{size:this.positionSize,gridResolution:this.opts.resolution,edgeTypes:!0}):this.opts.wrapLongitude?pc(mt(e),$t(e),{size:this.positionSize,maxLatitude:86,edgeTypes:!0}):e}return t}getGeometrySize(t){if(sn(t)){let e=0;for(const i of t)e+=this.getGeometrySize(i);return e}return mt(t).length/this.positionSize}getGeometryFromBuffer(t){return this.normalize||!this.buffers.indices?super.getGeometryFromBuffer(t):null}updateGeometryAttributes(t,e){if(t&&sn(t))for(const i of t){const o=this.getGeometrySize(i);e.geometrySize=o,this.updateGeometryAttributes(i,e),e.vertexStart+=o,e.indexStart=this.indexStarts[e.geometryIndex+1]}else{const i=t;this._updateIndices(i,e),this._updatePositions(i,e),this._updateVertexValid(i,e)}}_updateIndices(t,{geometryIndex:e,vertexStart:i,indexStart:o}){const{attributes:s,indexStarts:r,typedArrayManager:a}=this;let l=s.indices;if(!l||!t)return;let c=o;const u=tu(t,this.positionSize,this.opts.preproject,this.opts.full3d);l=a.allocate(l,o+u.length,{copy:!0});for(let f=0;f<u.length;f++)l[c++]=u[f]+i;r[e+1]=o+u.length,s.indices=l}_updatePositions(t,{vertexStart:e,geometrySize:i}){const{attributes:{positions:o},positionSize:s}=this;if(!o||!t)return;const r=mt(t);for(let a=e,l=0;l<i;a++,l++){const c=r[l*s],u=r[l*s+1],f=s>2?r[l*s+2]:0;o[a*3]=c,o[a*3+1]=u,o[a*3+2]=f}}_updateVertexValid(t,{vertexStart:e,geometrySize:i}){const{positionSize:o}=this,s=this.attributes.vertexValid,r=t&&$t(t);if(t&&t.edgeTypes?s.set(t.edgeTypes,e):s.fill(1,e,e+i),r)for(let a=0;a<r.length;a++)s[e+r[a]/o-1]=0;s[e+i-1]=0}}function sn(n){return Array.isArray(n)&&n.length>0&&!Number.isFinite(n[0])}const rn=`layout(std140) uniform solidPolygonUniforms {
  bool extruded;
  bool isWireframe;
  float elevationScale;
} solidPolygon;
`,iu={name:"solidPolygon",vs:rn,fs:rn,uniformTypes:{extruded:"f32",isWireframe:"f32",elevationScale:"f32"}},Lo=`in vec4 fillColors;
in vec4 lineColors;
in vec3 pickingColors;
out vec4 vColor;
struct PolygonProps {
vec3 positions;
vec3 positions64Low;
vec3 normal;
float elevations;
};
vec3 project_offset_normal(vec3 vector) {
if (project.coordinateSystem == COORDINATE_SYSTEM_LNGLAT ||
project.coordinateSystem == COORDINATE_SYSTEM_LNGLAT_OFFSETS) {
return normalize(vector * project.commonUnitsPerWorldUnit);
}
return project_normal(vector);
}
void calculatePosition(PolygonProps props) {
vec3 pos = props.positions;
vec3 pos64Low = props.positions64Low;
vec3 normal = props.normal;
vec4 colors = solidPolygon.isWireframe ? lineColors : fillColors;
geometry.worldPosition = props.positions;
geometry.pickingColor = pickingColors;
if (solidPolygon.extruded) {
pos.z += props.elevations * solidPolygon.elevationScale;
}
gl_Position = project_position_to_clipspace(pos, pos64Low, vec3(0.), geometry.position);
DECKGL_FILTER_GL_POSITION(gl_Position, geometry);
if (solidPolygon.extruded) {
#ifdef IS_SIDE_VERTEX
normal = project_offset_normal(normal);
#else
normal = project_normal(normal);
#endif
geometry.normal = normal;
vec3 lightColor = lighting_getLightColor(colors.rgb, project.cameraPosition, geometry.position.xyz, geometry.normal);
vColor = vec4(lightColor, colors.a * layer.opacity);
} else {
vColor = vec4(colors.rgb, colors.a * layer.opacity);
}
DECKGL_FILTER_COLOR(vColor, geometry);
}
`,nu=`#version 300 es
#define SHADER_NAME solid-polygon-layer-vertex-shader
in vec3 vertexPositions;
in vec3 vertexPositions64Low;
in float elevations;
${Lo}
void main(void) {
PolygonProps props;
props.positions = vertexPositions;
props.positions64Low = vertexPositions64Low;
props.elevations = elevations;
props.normal = vec3(0.0, 0.0, 1.0);
calculatePosition(props);
}
`,ou=`#version 300 es
#define SHADER_NAME solid-polygon-layer-vertex-shader-side
#define IS_SIDE_VERTEX
in vec2 positions;
in vec3 vertexPositions;
in vec3 nextVertexPositions;
in vec3 vertexPositions64Low;
in vec3 nextVertexPositions64Low;
in float elevations;
in float instanceVertexValid;
${Lo}
void main(void) {
if(instanceVertexValid < 0.5){
gl_Position = vec4(0.);
return;
}
PolygonProps props;
vec3 pos;
vec3 pos64Low;
vec3 nextPos;
vec3 nextPos64Low;
#if RING_WINDING_ORDER_CW == 1
pos = vertexPositions;
pos64Low = vertexPositions64Low;
nextPos = nextVertexPositions;
nextPos64Low = nextVertexPositions64Low;
#else
pos = nextVertexPositions;
pos64Low = nextVertexPositions64Low;
nextPos = vertexPositions;
nextPos64Low = vertexPositions64Low;
#endif
props.positions = mix(pos, nextPos, positions.x);
props.positions64Low = mix(pos64Low, nextPos64Low, positions.x);
props.normal = vec3(
pos.y - nextPos.y + (pos64Low.y - nextPos64Low.y),
nextPos.x - pos.x + (nextPos64Low.x - pos64Low.x),
0.0);
props.elevations = elevations * positions.y;
calculatePosition(props);
}
`,su=`#version 300 es
#define SHADER_NAME solid-polygon-layer-fragment-shader
precision highp float;
in vec4 vColor;
out vec4 fragColor;
void main(void) {
fragColor = vColor;
geometry.uv = vec2(0.);
DECKGL_FILTER_COLOR(fragColor, geometry);
}
`,Qt=[0,0,0,255],ru={filled:!0,extruded:!1,wireframe:!1,_normalize:!0,_windingOrder:"CW",_full3d:!1,elevationScale:{type:"number",min:0,value:1},getPolygon:{type:"accessor",value:n=>n.polygon},getElevation:{type:"accessor",value:1e3},getFillColor:{type:"accessor",value:Qt},getLineColor:{type:"accessor",value:Qt},material:!0},Bt={enter:(n,t)=>t.length?t.subarray(t.length-n.length):n};class ge extends N{getShaders(t){return super.getShaders({vs:t==="top"?nu:ou,fs:su,defines:{RING_WINDING_ORDER_CW:!this.props._normalize&&this.props._windingOrder==="CCW"?0:1},modules:[V,ae,W,iu]})}get wrapLongitude(){return!1}getBounds(){var t;return(t=this.getAttributeManager())==null?void 0:t.getBounds(["vertexPositions"])}initializeState(){const{viewport:t}=this.context;let{coordinateSystem:e}=this.props;const{_full3d:i}=this.props;t.isGeospatial&&e==="default"&&(e="lnglat");let o;e==="lnglat"&&(i?o=t.projectPosition.bind(t):o=t.projectFlat.bind(t)),this.setState({numInstances:0,polygonTesselator:new eu({preproject:o,fp64:this.use64bitPositions(),IndexType:Uint32Array})});const s=this.getAttributeManager(),r=!0;s.remove(["instancePickingColors"]),s.add({indices:{size:1,isIndexed:!0,update:this.calculateIndices,noAlloc:r},vertexPositions:{size:3,type:"float64",stepMode:"dynamic",fp64:this.use64bitPositions(),transition:Bt,accessor:"getPolygon",update:this.calculatePositions,noAlloc:r,shaderAttributes:{nextVertexPositions:{vertexOffset:1}}},instanceVertexValid:{size:1,type:"uint16",stepMode:"instance",update:this.calculateVertexValid,noAlloc:r},elevations:{size:1,stepMode:"dynamic",transition:Bt,accessor:"getElevation"},fillColors:{size:this.props.colorFormat.length,type:"unorm8",stepMode:"dynamic",transition:Bt,accessor:"getFillColor",defaultValue:Qt},lineColors:{size:this.props.colorFormat.length,type:"unorm8",stepMode:"dynamic",transition:Bt,accessor:"getLineColor",defaultValue:Qt},pickingColors:{size:4,type:"uint8",stepMode:"dynamic",accessor:(a,{index:l,target:c})=>this.encodePickingColor(a&&a.__source?a.__source.index:l,c)}})}getPickingInfo(t){const e=super.getPickingInfo(t),{index:i}=e,o=this.props.data;return o[0]&&o[0].__source&&(e.object=o.find(s=>s.__source.index===i)),e}disablePickingIndex(t){const e=this.props.data;if(e[0]&&e[0].__source)for(let i=0;i<e.length;i++)e[i].__source.index===t&&this._disablePickingIndex(i);else super.disablePickingIndex(t)}draw({uniforms:t}){const{extruded:e,filled:i,wireframe:o,elevationScale:s}=this.props,{topModel:r,sideModel:a,wireframeModel:l,polygonTesselator:c}=this.state,u={extruded:!!e,elevationScale:s,isWireframe:!1};l&&o&&(l.setInstanceCount(c.instanceCount-1),l.shaderInputs.setProps({solidPolygon:{...u,isWireframe:!0}}),l.draw(this.context.renderPass)),a&&i&&(a.setInstanceCount(c.instanceCount-1),a.shaderInputs.setProps({solidPolygon:u}),a.draw(this.context.renderPass)),r&&i&&(r.setVertexCount(c.vertexCount),r.shaderInputs.setProps({solidPolygon:u}),r.draw(this.context.renderPass))}updateState(t){var a;super.updateState(t),this.updateGeometry(t);const{props:e,oldProps:i,changeFlags:o}=t,s=this.getAttributeManager();(o.extensionsChanged||e.filled!==i.filled||e.extruded!==i.extruded)&&((a=this.state.models)==null||a.forEach(l=>l.destroy()),this.setState(this._getModels()),s.invalidateAll())}updateGeometry({props:t,oldProps:e,changeFlags:i}){if(i.dataChanged||i.updateTriggersChanged&&(i.updateTriggersChanged.all||i.updateTriggersChanged.getPolygon)){const{polygonTesselator:s}=this.state,r=t.data.attributes||{};s.updateGeometry({data:t.data,normalize:t._normalize,geometryBuffer:r.getPolygon,buffers:r,getGeometry:t.getPolygon,positionFormat:t.positionFormat,wrapLongitude:t.wrapLongitude,resolution:this.context.viewport.resolution,fp64:this.use64bitPositions(),dataChanged:i.dataChanged,full3d:t._full3d}),this.setState({numInstances:s.instanceCount,startIndices:s.vertexStarts}),i.dataChanged||this.getAttributeManager().invalidateAll()}}_getModels(){const{id:t,filled:e,extruded:i}=this.props;let o,s,r;if(e){const a=this.getShaders("top");a.defines.NON_INSTANCED_MODEL=1;const l=this.getAttributeManager().getBufferLayouts({isInstanced:!1});o=new z(this.context.device,{...a,id:`${t}-top`,topology:"triangle-list",bufferLayout:l,isIndexed:!0,userData:{excludeAttributes:{instanceVertexValid:!0}}})}if(i){const a=this.getAttributeManager().getBufferLayouts({isInstanced:!0});s=new z(this.context.device,{...this.getShaders("side"),id:`${t}-side`,bufferLayout:a,geometry:new $({topology:"triangle-strip",attributes:{positions:{size:2,value:new Float32Array([1,0,0,0,1,1,0,1])}}}),isInstanced:!0,userData:{excludeAttributes:{indices:!0}}}),r=new z(this.context.device,{...this.getShaders("side"),id:`${t}-wireframe`,bufferLayout:a,geometry:new $({topology:"line-strip",attributes:{positions:{size:2,value:new Float32Array([1,0,0,0,0,1,1,1])}}}),isInstanced:!0,userData:{excludeAttributes:{indices:!0}}})}return{models:[s,r,o].filter(Boolean),topModel:o,sideModel:s,wireframeModel:r}}calculateIndices(t){const{polygonTesselator:e}=this.state;t.startIndices=e.indexStarts,t.value=e.get("indices")}calculatePositions(t){const{polygonTesselator:e}=this.state;t.startIndices=e.vertexStarts,t.value=e.get("positions")}calculateVertexValid(t){t.value=this.state.polygonTesselator.get("vertexValid")}}ge.defaultProps=ru;ge.layerName="SolidPolygonLayer";function wo({data:n,getIndex:t,dataRange:e,replace:i}){const{startRow:o=0,endRow:s=1/0}=e,r=n.length;let a=r,l=r;for(let d=0;d<r;d++){const h=t(n[d]);if(a>d&&h>=o&&(a=d),h>=s){l=d;break}}let c=a;const f=l-a!==i.length?n.slice(l):void 0;for(let d=0;d<i.length;d++)n[c++]=i[d];if(f){for(let d=0;d<f.length;d++)n[c++]=f[d];n.length=c}return{startRow:a,endRow:a+i.length}}const Ao=[0,0,0,255],au=[0,0,0,255],lu={stroked:!0,filled:!0,extruded:!1,elevationScale:1,wireframe:!1,_normalize:!0,_windingOrder:"CW",lineWidthUnits:"meters",lineWidthScale:1,lineWidthMinPixels:0,lineWidthMaxPixels:Number.MAX_SAFE_INTEGER,lineJointRounded:!1,lineMiterLimit:4,getPolygon:{type:"accessor",value:n=>n.polygon},getFillColor:{type:"accessor",value:au},getLineColor:{type:"accessor",value:Ao},getLineWidth:{type:"accessor",value:1},getElevation:{type:"accessor",value:1e3},material:!0};class So extends ue{initializeState(){this.state={paths:[],pathsDiff:null},this.props.getLineDashArray&&T.removed("getLineDashArray","PathStyleExtension")()}updateState({changeFlags:t}){const e=t.dataChanged||t.updateTriggersChanged&&(t.updateTriggersChanged.all||t.updateTriggersChanged.getPolygon);if(e&&Array.isArray(t.dataChanged)){const i=this.state.paths.slice(),o=t.dataChanged.map(s=>wo({data:i,getIndex:r=>r.__source.index,dataRange:s,replace:this._getPaths(s)}));this.setState({paths:i,pathsDiff:o})}else e&&this.setState({paths:this._getPaths(),pathsDiff:null})}_getPaths(t={}){const{data:e,getPolygon:i,positionFormat:o,_normalize:s}=this.props,r=[],a=o==="XY"?2:3,{startRow:l,endRow:c}=t,{iterable:u,objectInfo:f}=ct(e,l,c);for(const d of u){f.index++;let h=i(d,f);s&&(h=Co(h,a));const{holeIndices:p}=h,g=h.positions||h;if(p)for(let m=0;m<=p.length;m++){const x=g.slice(p[m-1]||0,p[m]||g.length);r.push(this.getSubLayerRow({path:x},d,f.index))}else r.push(this.getSubLayerRow({path:g},d,f.index))}return r}renderLayers(){const{data:t,_dataDiff:e,stroked:i,filled:o,extruded:s,wireframe:r,_normalize:a,_windingOrder:l,elevationScale:c,transitions:u,positionFormat:f}=this.props,{lineWidthUnits:d,lineWidthScale:h,lineWidthMinPixels:p,lineWidthMaxPixels:g,lineJointRounded:m,lineMiterLimit:x,lineDashJustified:b}=this.props,{getFillColor:v,getLineColor:_,getLineWidth:C,getLineDashArray:w,getElevation:I,getPolygon:O,updateTriggers:L,material:E}=this.props,{paths:F,pathsDiff:U}=this.state,K=this.getSubLayerClass("fill",ge),ut=this.getSubLayerClass("stroke",de),Tt=this.shouldRenderSubLayer("fill",F)&&new K({_dataDiff:e,extruded:s,elevationScale:c,filled:o,wireframe:r,_normalize:a,_windingOrder:l,getElevation:I,getFillColor:v,getLineColor:s&&r?_:Ao,material:E,transitions:u},this.getSubLayerProps({id:"fill",updateTriggers:L&&{getPolygon:L.getPolygon,getElevation:L.getElevation,getFillColor:L.getFillColor,lineColors:s&&r,getLineColor:L.getLineColor}}),{data:t,positionFormat:f,getPolygon:O}),M=!s&&i&&this.shouldRenderSubLayer("stroke",F)&&new ut({_dataDiff:U&&(()=>U),widthUnits:d,widthScale:h,widthMinPixels:p,widthMaxPixels:g,jointRounded:m,miterLimit:x,dashJustified:b,_pathType:"loop",transitions:u&&{getWidth:u.getLineWidth,getColor:u.getLineColor,getPath:u.getPolygon},getColor:this.getSubLayerAccessor(_),getWidth:this.getSubLayerAccessor(C),getDashArray:this.getSubLayerAccessor(w)},this.getSubLayerProps({id:"stroke",updateTriggers:L&&{getWidth:L.getLineWidth,getColor:L.getLineColor,getDashArray:L.getLineDashArray}}),{data:F,positionFormat:f,getPath:S=>S.path});return[!s&&Tt,M,s&&Tt]}}So.layerName="PolygonLayer";So.defaultProps=lu;function cu(n,t){if(!n)return null;const e="startIndices"in n?n.startIndices[t]:t,i=n.featureIds.value[e];return e!==-1?uu(n,i,e):null}function uu(n,t,e){const i={properties:{...n.properties[t]}};for(const o in n.numericProps)i.properties[o]=n.numericProps[o].value[e];return i}function fu(n,t){const e={points:null,lines:null,polygons:null};for(const i in e){const o=n[i].globalFeatureIds.value;e[i]=new Uint8ClampedArray(o.length*4);const s=[];for(let r=0;r<o.length;r++)t(o[r],s),e[i][r*4+0]=s[0],e[i][r*4+1]=s[1],e[i][r*4+2]=s[2],e[i][r*4+3]=255}return e}const an=`layout(std140) uniform sdfUniforms {
  float gamma;
  bool enabled;
  float buffer;
  float outlineBuffer;
  vec4 outlineColor;
} sdf;
`,du={name:"sdf",vs:an,fs:an,uniformTypes:{gamma:"f32",enabled:"f32",buffer:"f32",outlineBuffer:"f32",outlineColor:"vec4<f32>"}},vt={none:0,start:1,center:2,end:3},hu=`layout(std140) uniform textUniforms {
  highp vec2 cutoffPixels;
  highp ivec2 align;
  highp float fontSize;
  bool flipY;
} text;

#define ALIGN_MODE_START ${vt.start}
#define ALIGN_MODE_CENTER ${vt.center}
#define ALIGN_MODE_END ${vt.end}
`,To={name:"text",vs:hu,getUniforms:({contentCutoffPixels:n=[0,0],contentAlignHorizontal:t="none",contentAlignVertical:e="none",fontSize:i,viewport:o})=>({cutoffPixels:n,align:[vt[t],vt[e]],fontSize:i,flipY:(o==null?void 0:o.flipY)??!1}),uniformTypes:{cutoffPixels:"vec2<f32>",align:"vec2<i32>",fontSize:"f32",flipY:"f32"}},pu=`#version 300 es
#define SHADER_NAME multi-icon-layer-vertex-shader
in vec2 positions;
in vec3 instancePositions;
in vec3 instancePositions64Low;
in float instanceSizes;
in float instanceAngles;
in vec4 instanceColors;
in vec3 instancePickingColors;
in vec4 instanceIconFrames;
in float instanceColorModes;
in vec2 instanceOffsets;
in vec2 instancePixelOffset;
in vec4 instanceClipRect;
out float vColorMode;
out vec4 vColor;
out vec2 vTextureCoords;
out vec2 uv;
vec2 rotate_by_angle(vec2 vertex, float angle) {
float angle_radian = angle * PI / 180.0;
float cos_angle = cos(angle_radian);
float sin_angle = sin(angle_radian);
mat2 rotationMatrix = mat2(cos_angle, -sin_angle, sin_angle, cos_angle);
return rotationMatrix * vertex;
}
float getPixelOffsetFromAlignment(float anchor, float extent, float clipStart, float clipEnd, int mode) {
if (clipEnd < clipStart) return 0.0;
if (mode == ALIGN_MODE_START) {
return max(- (anchor + clipStart), 0.0);
}
if (mode == ALIGN_MODE_CENTER) {
float _min = max(0., anchor + clipStart);
float _max = min(extent, anchor + clipEnd);
return _min < _max ? (_min + _max) / 2.0 - anchor : 0.0;
}
if (mode == ALIGN_MODE_END) {
return min(extent - (anchor + clipEnd), 0.);
}
return 0.0;
}
void main(void) {
geometry.worldPosition = instancePositions;
geometry.uv = positions;
geometry.pickingColor = instancePickingColors;
uv = positions;
vec2 iconSize = instanceIconFrames.zw;
float sizePixels = clamp(
project_size_to_pixel(instanceSizes * icon.sizeScale, icon.sizeUnits),
icon.sizeMinPixels, icon.sizeMaxPixels
);
float instanceScale = sizePixels / text.fontSize;
vec2 pixelOffset = positions / 2.0 * iconSize + instanceOffsets;
pixelOffset = rotate_by_angle(pixelOffset, instanceAngles) * instanceScale;
pixelOffset += instancePixelOffset;
pixelOffset.y *= -1.0;
vec2 anchorPosScreen;
if (icon.billboard)  {
gl_Position = project_position_to_clipspace(instancePositions, instancePositions64Low, vec3(0.0), geometry.position);
anchorPosScreen = gl_Position.xy / gl_Position.w;
DECKGL_FILTER_GL_POSITION(gl_Position, geometry);
vec3 offset = vec3(pixelOffset, 0.0);
DECKGL_FILTER_SIZE(offset, geometry);
gl_Position.xy += project_pixel_size_to_clipspace(offset.xy);
} else {
vec3 offset_common = vec3(project_pixel_size(pixelOffset), 0.0);
if (text.flipY) {
offset_common.y *= -1.;
}
DECKGL_FILTER_SIZE(offset_common, geometry);
vec4 anchorPos = project_position_to_clipspace(instancePositions, instancePositions64Low, vec3(0.0));
anchorPosScreen = anchorPos.xy / anchorPos.w;
gl_Position = project_position_to_clipspace(instancePositions, instancePositions64Low, offset_common, geometry.position);
DECKGL_FILTER_GL_POSITION(gl_Position, geometry);
}
anchorPosScreen = vec2(anchorPosScreen.x + 1.0, 1.0 - anchorPosScreen.y) / 2.0 * project.viewportSize / project.devicePixelRatio;
vec2 xy = project_size_to_pixel(instanceClipRect.xy);
vec2 wh = project_size_to_pixel(instanceClipRect.zw);
if (text.flipY) {
xy.y = -xy.y - wh.y;
}
if (text.align.x > 0 || text.align.y > 0) {
vec2 viewportPixels = project.viewportSize / project.devicePixelRatio;
vec2 scrollPixels = vec2(
getPixelOffsetFromAlignment(anchorPosScreen.x, viewportPixels.x, xy.x, xy.x + wh.x, text.align.x),
-getPixelOffsetFromAlignment(anchorPosScreen.y, viewportPixels.y, -xy.y - wh.y, -xy.y, text.align.y)
);
pixelOffset += scrollPixels;
gl_Position.xy += project_pixel_size_to_clipspace(scrollPixels);
}
if (instanceClipRect.z >= 0.) {
if (pixelOffset.x < xy.x || pixelOffset.x > xy.x + wh.x) {
gl_Position = vec4(0.0);
}
else if (text.cutoffPixels.x > 0.) {
float vpWidth = project.viewportSize.x / project.devicePixelRatio;
float l = max(anchorPosScreen.x + xy.x, 0.0);
float r = min(anchorPosScreen.x + xy.x + wh.x, vpWidth);
if (r - l < text.cutoffPixels.x) {
gl_Position = vec4(0.0);
}
}
}
if (instanceClipRect.w >= 0.) {
if (pixelOffset.y < xy.y || pixelOffset.y > xy.y + wh.y) {
gl_Position = vec4(0.0);
}
else if (text.cutoffPixels.y > 0.) {
float vpHeight = project.viewportSize.y / project.devicePixelRatio;
float t = max(anchorPosScreen.y - xy.y - wh.y, 0.0);
float b = min(anchorPosScreen.y - xy.y, vpHeight);
if (b - t < text.cutoffPixels.y) {
gl_Position = vec4(0.0);
}
}
}
vTextureCoords = mix(
instanceIconFrames.xy,
instanceIconFrames.xy + iconSize,
(positions.xy + 1.0) / 2.0
) / icon.iconsTextureDim;
vColor = instanceColors;
DECKGL_FILTER_COLOR(vColor, geometry);
vColorMode = instanceColorModes;
}
`,gu=`#version 300 es
#define SHADER_NAME multi-icon-layer-fragment-shader
precision highp float;
uniform sampler2D iconsTexture;
in vec4 vColor;
in vec2 vTextureCoords;
in vec2 uv;
out vec4 fragColor;
void main(void) {
geometry.uv = uv;
if (!bool(picking.isActive)) {
float alpha = texture(iconsTexture, vTextureCoords).a;
vec4 color = vColor;
if (sdf.enabled) {
float distance = alpha;
alpha = smoothstep(sdf.buffer - sdf.gamma, sdf.buffer + sdf.gamma, distance);
if (sdf.outlineBuffer > 0.0) {
float inFill = alpha;
float inBorder = smoothstep(sdf.outlineBuffer - sdf.gamma, sdf.outlineBuffer + sdf.gamma, distance);
color = mix(sdf.outlineColor, vColor, inFill);
alpha = inBorder;
}
}
float a = alpha * color.a;
if (a < icon.alphaCutoff) {
discard;
}
fragColor = vec4(color.rgb, a * layer.opacity);
}
DECKGL_FILTER_COLOR(fragColor, geometry);
}
`,Se=192/256,mu={getIconOffsets:{type:"accessor",value:n=>n.offsets},getContentBox:{type:"accessor",value:[0,0,-1,-1]},fontSize:1,alphaCutoff:.001,smoothing:.1,outlineWidth:0,outlineColor:{type:"color",value:[0,0,0,255]},contentCutoffPixels:{type:"array",value:[0,0]},contentAlignHorizontal:"none",contentAlignVertical:"none"};class si extends fe{getShaders(){const t=super.getShaders();return{...t,modules:[...t.modules,To,du],vs:pu,fs:gu}}initializeState(){super.initializeState();const t=this.getAttributeManager(),e=t.attributes.instanceIconDefs;e.settings.update=this.calculateInstanceIconDefs,t.addInstanced({instancePickingColors:{type:"uint8",size:4,accessor:(i,{index:o,target:s})=>this.encodePickingColor(o,s)},instanceClipRect:{size:4,accessor:"getContentBox",defaultValue:[0,0,-1,-1]}})}updateState(t){super.updateState(t);const{props:e,oldProps:i,changeFlags:o}=t,{outlineColor:s}=e;if(o.updateTriggersChanged&&(o.updateTriggersChanged.getIcon||o.updateTriggersChanged.getIconOffsets)&&this.getAttributeManager().invalidate("instanceIconDefs"),s!==i.outlineColor){const r=[s[0]/255,s[1]/255,s[2]/255,(s[3]??255)/255];this.setState({outlineColor:r})}!e.sdf&&e.outlineWidth&&T.warn(`${this.id}: fontSettings.sdf is required to render outline`)()}draw(t){const{sdf:e,smoothing:i,fontSize:o,outlineWidth:s,contentCutoffPixels:r,contentAlignHorizontal:a,contentAlignVertical:l}=this.props,{outlineColor:c}=this.state,u=s?Math.max(i,Se*(1-s)):-1,f=this.state.model,d={buffer:Se,outlineBuffer:u,gamma:i,enabled:!!e,outlineColor:c},h={contentCutoffPixels:r,contentAlignHorizontal:a,contentAlignVertical:l,fontSize:o,viewport:this.context.viewport};if(f.shaderInputs.setProps({sdf:d,text:h}),super.draw(t),e&&s){const{iconManager:p}=this.state;p.getTexture()&&(f.shaderInputs.setProps({sdf:{...d,outlineBuffer:Se}}),f.draw(this.context.renderPass))}}calculateInstanceIconDefs(t,{startRow:e,endRow:i}){const{data:o,getIcon:s,getIconOffsets:r}=this.props;let a=t.getVertexOffset(e);const l=t.value,{iterable:c,objectInfo:u}=ct(o,e,i);for(const f of c){u.index++;const d=s(f,u),h=r(f,u);if(d){let p=0;for(const g of Array.from(d)){const m=super.getInstanceIconDef(g);m[0]=h[p*2],m[1]+=h[p*2+1],m[6]=1,l.set(m,a),a+=t.size,p++}}}}}si.defaultProps=mu;si.layerName="MultiIconLayer";const _t=1e20,ri=new Float64Array(256);for(let n=0;n<256;n++){const t=.5-Math.pow(n/255,.45454545454545453);ri[n]=t*Math.abs(t)}ri[255]=-_t;class yu{constructor({fontSize:t=24,buffer:e=3,radius:i=8,cutoff:o=.25,fontFamily:s="sans-serif",fontWeight:r="normal",fontStyle:a="normal",lang:l=null}={}){this.buffer=e,this.radius=i,this.cutoff=o,this.lang=l;const c=this.size=t+e*4,u=this._createCanvas(c),f=this.ctx=u.getContext("2d",{willReadFrequently:!0});f.font=`${a} ${r} ${t}px ${s}`,f.textBaseline="alphabetic",f.textAlign="left",f.fillStyle="black",this.gridOuter=new Float64Array(c*c),this.gridInner=new Float64Array(c*c),this.f=new Float64Array(c),this.z=new Float64Array(c+1),this.v=new Uint16Array(c)}_createCanvas(t){if(typeof OffscreenCanvas<"u")return new OffscreenCanvas(t,t);const e=document.createElement("canvas");return e.width=e.height=t,e}draw(t){const{width:e,actualBoundingBoxAscent:i,actualBoundingBoxDescent:o,actualBoundingBoxLeft:s,actualBoundingBoxRight:r}=this.ctx.measureText(t),a=Math.ceil(i),l=Math.floor(-s),c=Math.max(0,Math.min(this.size-this.buffer,Math.ceil(r)-l)),u=Math.max(0,Math.min(this.size-this.buffer,a+Math.ceil(o))),f=c+2*this.buffer,d=u+2*this.buffer,h=Math.max(f*d,0),p=new Uint8ClampedArray(h),g={data:p,width:f,height:d,glyphWidth:c,glyphHeight:u,glyphTop:a,glyphLeft:l,glyphAdvance:e};if(c===0||u===0)return g;const{ctx:m,buffer:x,gridInner:b,gridOuter:v}=this;this.lang&&(m.lang=this.lang),m.clearRect(x,x,c,u),m.fillText(t,x-l,x+a);const _=m.getImageData(x,x,c,u);v.fill(_t,0,h),b.fill(0,0,h);let C=3;for(let L=0;L<u;L++){let E=(L+x)*f+x;for(let F=0;F<c;F++,C+=4,E++){const U=_.data[C];if(U===0)continue;const K=ri[U];v[E]=Math.max(0,K),b[E]=Math.max(0,-K)}}ln(v,0,0,f,d,f,this.f,this.v,this.z);const w=Math.min(x,1);ln(b,x-w,x-w,c+2*w,u+2*w,f,this.f,this.v,this.z);const I=255/this.radius,O=255*(1-this.cutoff);for(let L=0;L<h;L++){const E=Math.sqrt(v[L])-Math.sqrt(b[L]);p[L]=Math.round(O-I*E)}return g}}function ln(n,t,e,i,o,s,r,a,l){for(let c=t;c<t+i;c++)cn(n,e*s+c,s,o,r,a,l);for(let c=e;c<e+o;c++)cn(n,c*s+t,1,i,r,a,l)}function cn(n,t,e,i,o,s,r){s[0]=0,r[0]=-_t,r[1]=_t,o[0]=n[t];for(let a=1,l=0,c=0;a<i;a++){o[a]=n[t+a*e];const u=a*a;do{const f=s[l];c=(o[a]-o[f]+u-f*f)/(a-f)/2}while(c<=r[l]&&--l>-1);l++,s[l]=a,r[l]=c,r[l+1]=_t}for(let a=0,l=0;a<i;a++){for(;r[l+1]<a;)l++;const c=s[l],u=a-c;n[t+a*e]=o[c]+u*u}}const vu=32,_u=[];function xu(n){return Math.pow(2,Math.ceil(Math.log2(n)))}function bu({characterSet:n,measureText:t,buffer:e,maxCanvasWidth:i,mapping:o={},xOffset:s=0,yOffsetMin:r=0,yOffsetMax:a=0}){let l=s,c=r,u=a;for(const f of n)if(!o[f]){const{advance:d,width:h,ascent:p,descent:g}=t(f),m=p+g;l+h+e*2>i&&(l=0,c=u),o[f]={x:l+e,y:c+e,width:h,height:m,advance:d,anchorX:h/2,anchorY:p},l+=h+e*2,u=Math.max(u,c+m+e*2)}return{mapping:o,xOffset:l,yOffsetMin:c,yOffsetMax:u,canvasHeight:xu(u)}}function Eo(n,t,e,i){var s;let o=0;for(let r=t;r<e;r++){const a=n[r];o+=((s=i[a])==null?void 0:s.advance)||0}return o}function Io(n,t,e,i,o,s){let r=t,a=0;for(let l=t;l<e;l++){const c=Eo(n,l,l+1,o);a+c>i&&(r<l&&s.push(l),r=l,a=0),a+=c}return a}function Pu(n,t,e,i,o,s){let r=t,a=t,l=t,c=0;for(let u=t;u<e;u++)if((n[u]===" "||n[u+1]===" "||u+1===e)&&(l=u+1),l>a){let f=Eo(n,a,l,o);c+f>i&&(r<a&&(s.push(a),r=a,c=0),f>i&&(f=Io(n,a,l,i,o,s),r=s[s.length-1])),a=l,c+=f}return c}function Cu(n,t,e,i,o=0,s){s===void 0&&(s=n.length);const r=[];return t==="break-all"?Io(n,o,s,e,i,r):Pu(n,o,s,e,i,r),r}function Lu(n,t,e,i,o,s){let r=0,a=0;for(let l=t;l<e;l++){const c=n[l],u=i[c];u&&(a=Math.max(a,u.height))}for(let l=t;l<e;l++){const c=n[l],u=i[c];u?(o[l]=r+u.anchorX,r+=u.advance):(T.warn(`Missing character: ${c} (${c.codePointAt(0)})`)(),o[l]=r,r+=vu)}s[0]=r,s[1]=a}function wu(n,t,e,i,o,s){const r=Array.from(n),a=r.length,l=new Array(a),c=new Array(a),u=new Array(a),f=(i==="break-word"||i==="break-all")&&isFinite(o)&&o>0,d=[0,0],h=[0,0];let p=0,g=t+e/2,m=0,x=0;for(let b=0;b<=a;b++){const v=r[b];if((v===`
`||b===a)&&(x=b),x>m){const _=f?Cu(r,i,o,s,m,x):_u;for(let C=0;C<=_.length;C++){const w=C===0?m:_[C-1],I=C<_.length?_[C]:x;Lu(r,w,I,s,l,h);for(let O=w;O<I;O++)c[O]=g,u[O]=h[0];p++,g+=e,d[0]=Math.max(d[0],h[0])}m=x}v===`
`&&(l[m]=0,c[m]=0,u[m]=0,m++)}return d[1]=p*e,{x:l,y:c,rowWidth:u,size:d}}function Au({value:n,length:t,stride:e,offset:i,startIndices:o,characterSet:s}){const r=n.BYTES_PER_ELEMENT,a=e?e/r:1,l=i?i/r:0,c=o[t]||Math.ceil((n.length-l)/a),u=s&&new Set,f=new Array(t);let d=n;if(a>1||l>0){const h=n.constructor;d=new h(c);for(let p=0;p<c;p++)d[p]=n[p*a+l]}for(let h=0;h<t;h++){const p=o[h],g=o[h+1]||c,m=d.subarray(p,g);f[h]=String.fromCodePoint.apply(null,m),u&&m.forEach(u.add,u)}if(u)for(const h of u)s.add(String.fromCodePoint(h));return{texts:f,characterCount:c}}class Oo{constructor(t=5){this._cache={},this._order=[],this.limit=t}get(t){const e=this._cache[t];return e&&(this._deleteOrder(t),this._appendOrder(t)),e}set(t,e){this._cache[t]?(this.delete(t),this._cache[t]=e,this._appendOrder(t)):(Object.keys(this._cache).length===this.limit&&this.delete(this._order[0]),this._cache[t]=e,this._appendOrder(t))}delete(t){this._cache[t]&&(delete this._cache[t],this._deleteOrder(t))}_deleteOrder(t){const e=this._order.indexOf(t);e>=0&&this._order.splice(e,1)}_appendOrder(t){this._order.push(t)}}function Su(){const n=[];for(let t=32;t<128;t++)n.push(String.fromCharCode(t));return n}const at={fontFamily:"Monaco, monospace",fontWeight:"normal",characterSet:Su(),fontSize:64,buffer:4,sdf:!1,cutoff:.25,radius:12,smoothing:.1},un=1024,fn=.9,dn=.3,Mo=3;let te=new Oo(Mo);function Tu(n,t){let e;typeof t=="string"?e=new Set(Array.from(t)):e=new Set(t);const i=te.get(n);if(!i)return e;for(const o in i.mapping)e.has(o)&&e.delete(o);return e}function Eu(n,t){for(let e=0;e<n.length;e++)t.data[4*e+3]=n[e]}function hn(n,t,e,i){n.font=`${i} ${e}px ${t}`,n.fillStyle="#000",n.textBaseline="alphabetic",n.textAlign="left"}function Iu(n,t,e){if(e===void 0){const o=n.measureText("A");return o.fontBoundingBoxAscent?{advance:0,width:0,ascent:Math.ceil(o.fontBoundingBoxAscent),descent:Math.ceil(o.fontBoundingBoxDescent)}:{advance:0,width:0,ascent:t*fn,descent:t*dn}}const i=n.measureText(e);return i.actualBoundingBoxAscent?{advance:i.width,width:Math.ceil(i.actualBoundingBoxRight-i.actualBoundingBoxLeft),ascent:Math.ceil(i.actualBoundingBoxAscent),descent:Math.ceil(i.actualBoundingBoxDescent)}:{advance:i.width,width:i.width,ascent:t*fn,descent:t*dn}}function Ou(n){T.assert(Number.isFinite(n)&&n>=Mo,"Invalid cache limit"),te=new Oo(n)}class Mu{constructor(){this.props={...at}}get atlas(){return this._atlas}get mapping(){return this._atlas&&this._atlas.mapping}setProps(t={}){Object.assign(this.props,t),t._getFontRenderer&&(this._getFontRenderer=t._getFontRenderer),this._key=this._getKey();const e=Tu(this._key,this.props.characterSet),i=te.get(this._key);if(i&&e.size===0){this._atlas!==i&&(this._atlas=i);return}const o=this._generateFontAtlas(e,i);this._atlas=o,te.set(this._key,o)}_generateFontAtlas(t,e){const{fontFamily:i,fontWeight:o,fontSize:s,buffer:r,sdf:a,radius:l,cutoff:c}=this.props;let u=e&&e.data;u||(u=document.createElement("canvas"),u.width=un);const f=u.getContext("2d",{willReadFrequently:!0});hn(f,i,s,o);const d=_=>Iu(f,s,_);let h;this._getFontRenderer?h=this._getFontRenderer(this.props):a&&(h={measure:d,draw:Ru(this.props)});const{mapping:p,canvasHeight:g,xOffset:m,yOffsetMin:x,yOffsetMax:b}=bu({measureText:_=>h?h.measure(_):d(_),buffer:r,characterSet:t,maxCanvasWidth:un,...e&&{mapping:e.mapping,xOffset:e.xOffset,yOffsetMin:e.yOffsetMin,yOffsetMax:e.yOffsetMax}});if(u.height!==g){const _=u.height>0?f.getImageData(0,0,u.width,u.height):null;u.height=g,_&&f.putImageData(_,0,0)}if(hn(f,i,s,o),h)for(const _ of t){const C=p[_],{data:w,left:I=0,top:O=0}=h.draw(_),L=C.x-I,E=C.y-O,F=Math.max(0,Math.round(L)),U=Math.max(0,Math.round(E)),K=Math.min(w.width,u.width-F),ut=Math.min(w.height,u.height-U);f.putImageData(w,F,U,0,0,K,ut),C.x+=F-L,C.y+=U-E}else for(const _ of t){const C=p[_];f.fillText(_,C.x,C.y+C.anchorY)}const v=h?h.measure():d();return{baselineOffset:(v.ascent-v.descent)/2,xOffset:m,yOffsetMin:x,yOffsetMax:b,mapping:p,data:u,width:u.width,height:u.height}}_getKey(){const{fontFamily:t,fontWeight:e,fontSize:i,buffer:o,sdf:s,radius:r,cutoff:a}=this.props;return s?`${t} ${e} ${i} ${o} ${r} ${a}`:`${t} ${e} ${i} ${o}`}}function Ru({fontSize:n,buffer:t,radius:e,cutoff:i,fontFamily:o,fontWeight:s}){const r=new yu({fontSize:n,buffer:t,radius:e,cutoff:i,fontFamily:o,fontWeight:`${s}`});return a=>{const{data:l,width:c,height:u}=r.draw(a),f=new ImageData(c,u);return Eu(l,f),{data:f,left:t,top:t}}}const pn=`layout(std140) uniform textBackgroundUniforms {
  bool billboard;
  float sizeScale;
  float sizeMinPixels;
  float sizeMaxPixels;
  vec4 borderRadius;
  vec4 padding;
  highp int sizeUnits;
  bool stroked;
} textBackground;
`,zu={name:"textBackground",vs:pn,fs:pn,uniformTypes:{billboard:"f32",sizeScale:"f32",sizeMinPixels:"f32",sizeMaxPixels:"f32",borderRadius:"vec4<f32>",padding:"vec4<f32>",sizeUnits:"i32",stroked:"f32"}},Fu=`#version 300 es
#define SHADER_NAME text-background-layer-vertex-shader
in vec2 positions;
in vec3 instancePositions;
in vec3 instancePositions64Low;
in vec4 instanceRects;
in vec4 instanceClipRect;
in float instanceSizes;
in float instanceAngles;
in vec2 instancePixelOffsets;
in float instanceLineWidths;
in vec4 instanceFillColors;
in vec4 instanceLineColors;
in vec3 instancePickingColors;
out vec4 vFillColor;
out vec4 vLineColor;
out float vLineWidth;
out vec2 uv;
out vec2 dimensions;
vec2 rotate_by_angle(vec2 vertex, float angle) {
float angle_radian = radians(angle);
float cos_angle = cos(angle_radian);
float sin_angle = sin(angle_radian);
mat2 rotationMatrix = mat2(cos_angle, -sin_angle, sin_angle, cos_angle);
return rotationMatrix * vertex;
}
void main(void) {
geometry.worldPosition = instancePositions;
geometry.uv = positions;
geometry.pickingColor = instancePickingColors;
uv = positions;
vLineWidth = instanceLineWidths;
float sizePixels = clamp(
project_size_to_pixel(instanceSizes * textBackground.sizeScale, textBackground.sizeUnits),
textBackground.sizeMinPixels, textBackground.sizeMaxPixels
);
float instanceScale = sizePixels / text.fontSize;
dimensions = instanceRects.zw * instanceScale + textBackground.padding.xy + textBackground.padding.zw;
vec2 pixelOffset = (positions * instanceRects.zw + instanceRects.xy) * instanceScale + mix(-textBackground.padding.xy, textBackground.padding.zw, positions);
pixelOffset = rotate_by_angle(pixelOffset, instanceAngles);
pixelOffset += instancePixelOffsets;
pixelOffset.y *= -1.0;
vec2 xy = project_size_to_pixel(instanceClipRect.xy);
vec2 wh = project_size_to_pixel(instanceClipRect.zw);
if (text.flipY) {
xy.y = -xy.y - wh.y;
}
if (instanceClipRect.z >= 0.0) {
dimensions.x = wh.x;
pixelOffset.x = xy.x + uv.x * wh.x + mix(-textBackground.padding.x, textBackground.padding.z, uv.x);
}
if (instanceClipRect.w >= 0.0) {
dimensions.y = wh.y;
pixelOffset.y = xy.y + uv.y * wh.y + mix(-textBackground.padding.y, textBackground.padding.w, uv.y);
}
if (textBackground.billboard)  {
gl_Position = project_position_to_clipspace(instancePositions, instancePositions64Low, vec3(0.0), geometry.position);
DECKGL_FILTER_GL_POSITION(gl_Position, geometry);
vec3 offset = vec3(pixelOffset, 0.0);
DECKGL_FILTER_SIZE(offset, geometry);
gl_Position.xy += project_pixel_size_to_clipspace(offset.xy);
} else {
vec3 offset_common = vec3(project_pixel_size(pixelOffset), 0.0);
if (text.flipY) {
offset_common.y *= -1.;
}
DECKGL_FILTER_SIZE(offset_common, geometry);
gl_Position = project_position_to_clipspace(instancePositions, instancePositions64Low, offset_common, geometry.position);
DECKGL_FILTER_GL_POSITION(gl_Position, geometry);
}
vFillColor = vec4(instanceFillColors.rgb, instanceFillColors.a * layer.opacity);
DECKGL_FILTER_COLOR(vFillColor, geometry);
vLineColor = vec4(instanceLineColors.rgb, instanceLineColors.a * layer.opacity);
DECKGL_FILTER_COLOR(vLineColor, geometry);
}
`,ku=`#version 300 es
#define SHADER_NAME text-background-layer-fragment-shader
precision highp float;
in vec4 vFillColor;
in vec4 vLineColor;
in float vLineWidth;
in vec2 uv;
in vec2 dimensions;
out vec4 fragColor;
float round_rect(vec2 p, vec2 size, vec4 radii) {
vec2 pixelPositionCB = (p - 0.5) * size;
vec2 sizeCB = size * 0.5;
float maxBorderRadius = min(size.x, size.y) * 0.5;
vec4 borderRadius = vec4(min(radii, maxBorderRadius));
borderRadius.xy =
(pixelPositionCB.x > 0.0) ? borderRadius.xy : borderRadius.zw;
borderRadius.x = (pixelPositionCB.y > 0.0) ? borderRadius.x : borderRadius.y;
vec2 q = abs(pixelPositionCB) - sizeCB + borderRadius.x;
return -(min(max(q.x, q.y), 0.0) + length(max(q, 0.0)) - borderRadius.x);
}
float rect(vec2 p, vec2 size) {
vec2 pixelPosition = p * size;
return min(min(pixelPosition.x, size.x - pixelPosition.x),
min(pixelPosition.y, size.y - pixelPosition.y));
}
vec4 get_stroked_fragColor(float dist) {
float isBorder = smoothedge(dist, vLineWidth);
return mix(vFillColor, vLineColor, isBorder);
}
void main(void) {
geometry.uv = uv;
if (textBackground.borderRadius != vec4(0.0)) {
float distToEdge = round_rect(uv, dimensions, textBackground.borderRadius);
float shapeAlpha = smoothedge(-distToEdge, 0.0);
if (shapeAlpha == 0.0) {
discard;
}
if (textBackground.stroked) {
fragColor = get_stroked_fragColor(distToEdge);
} else {
fragColor = vFillColor;
}
fragColor.a *= shapeAlpha;
} else {
if (textBackground.stroked) {
float distToEdge = rect(uv, dimensions);
fragColor = get_stroked_fragColor(distToEdge);
} else {
fragColor = vFillColor;
}
}
DECKGL_FILTER_COLOR(fragColor, geometry);
}
`,Bu={billboard:!0,sizeScale:1,sizeUnits:"pixels",sizeMinPixels:0,sizeMaxPixels:Number.MAX_SAFE_INTEGER,fontSize:1,borderRadius:{type:"object",value:0},padding:{type:"array",value:[0,0,0,0]},getPosition:{type:"accessor",value:n=>n.position},getSize:{type:"accessor",value:1},getAngle:{type:"accessor",value:0},getPixelOffset:{type:"accessor",value:[0,0]},getBoundingRect:{type:"accessor",value:[0,0,0,0]},getClipRect:{type:"accessor",value:[0,0,-1,-1]},getFillColor:{type:"accessor",value:[0,0,0,255]},getLineColor:{type:"accessor",value:[0,0,0,255]},getLineWidth:{type:"accessor",value:1}};class ai extends N{getShaders(){return super.getShaders({vs:Fu,fs:ku,modules:[V,W,zu,To]})}initializeState(){this.getAttributeManager().addInstanced({instancePositions:{size:3,type:"float64",fp64:this.use64bitPositions(),transition:!0,accessor:"getPosition"},instanceSizes:{size:1,transition:!0,accessor:"getSize",defaultValue:1},instanceAngles:{size:1,transition:!0,accessor:"getAngle"},instanceRects:{size:4,accessor:"getBoundingRect"},instanceClipRect:{size:4,accessor:"getClipRect",defaultValue:[0,0,-1,-1]},instancePixelOffsets:{size:2,transition:!0,accessor:"getPixelOffset"},instanceFillColors:{size:4,transition:!0,type:"unorm8",accessor:"getFillColor",defaultValue:[0,0,0,255]},instanceLineColors:{size:4,transition:!0,type:"unorm8",accessor:"getLineColor",defaultValue:[0,0,0,255]},instanceLineWidths:{size:1,transition:!0,accessor:"getLineWidth",defaultValue:1}})}updateState(t){var i;super.updateState(t);const{changeFlags:e}=t;e.extensionsChanged&&((i=this.state.model)==null||i.destroy(),this.state.model=this._getModel(),this.getAttributeManager().invalidateAll())}draw({uniforms:t}){const{billboard:e,sizeScale:i,sizeUnits:o,sizeMinPixels:s,sizeMaxPixels:r,getLineWidth:a,fontSize:l}=this.props;let{padding:c,borderRadius:u}=this.props;c.length<4&&(c=[c[0],c[1],c[0],c[1]]),Array.isArray(u)||(u=[u,u,u,u]);const f=this.state.model,d={billboard:e,stroked:!!a,borderRadius:u,padding:c,sizeUnits:G[o],sizeScale:i,sizeMinPixels:s,sizeMaxPixels:r},h={fontSize:l,viewport:this.context.viewport};f.shaderInputs.setProps({textBackground:d,text:h}),f.draw(this.context.renderPass)}_getModel(){const t=[0,0,1,0,0,1,1,1];return new z(this.context.device,{...this.getShaders(),id:this.props.id,bufferLayout:this.getAttributeManager().getBufferLayouts(),geometry:new $({topology:"triangle-strip",vertexCount:4,attributes:{positions:{size:2,value:new Float32Array(t)}}}),isInstanced:!0})}}ai.defaultProps=Bu;ai.layerName="TextBackgroundLayer";const gn={start:1,middle:0,end:-1},mn={top:1,center:0,bottom:-1},Te=[0,0,0,255],Nu=1,Uu={billboard:!0,sizeScale:1,sizeUnits:"pixels",sizeMinPixels:0,sizeMaxPixels:Number.MAX_SAFE_INTEGER,background:!1,getBackgroundColor:{type:"accessor",value:[255,255,255,255]},getBorderColor:{type:"accessor",value:Te},getBorderWidth:{type:"accessor",value:0},backgroundBorderRadius:{type:"object",value:0},backgroundPadding:{type:"array",value:[0,0,0,0]},characterSet:{type:"object",value:at.characterSet},fontFamily:at.fontFamily,fontWeight:at.fontWeight,lineHeight:Nu,outlineWidth:{type:"number",value:0,min:0},outlineColor:{type:"color",value:Te},fontSettings:{type:"object",value:{},compare:1},wordBreak:"break-word",maxWidth:{type:"number",value:-1},contentCutoffPixels:{type:"array",value:[0,0]},contentAlignHorizontal:"none",contentAlignVertical:"none",getText:{type:"accessor",value:n=>n.text},getPosition:{type:"accessor",value:n=>n.position},getColor:{type:"accessor",value:Te},getSize:{type:"accessor",value:32},getAngle:{type:"accessor",value:0},getTextAnchor:{type:"accessor",value:"middle"},getAlignmentBaseline:{type:"accessor",value:"center"},getPixelOffset:{type:"accessor",value:[0,0]},getContentBox:{type:"accessor",value:[0,0,-1,-1]},backgroundColor:{deprecatedFor:["background","getBackgroundColor"]}};class li extends ue{constructor(){super(...arguments),this.getBoundingRect=(t,e)=>{const{size:[i,o]}=this.transformParagraph(t,e),{getTextAnchor:s,getAlignmentBaseline:r}=this.props,a=gn[typeof s=="function"?s(t,e):s],l=mn[typeof r=="function"?r(t,e):r];return[(a-1)*i/2,(l-1)*o/2,i,o]},this.getIconOffsets=(t,e)=>{const{getTextAnchor:i,getAlignmentBaseline:o}=this.props,{x:s,y:r,rowWidth:a,size:[,l]}=this.transformParagraph(t,e),c=gn[typeof i=="function"?i(t,e):i],u=mn[typeof o=="function"?o(t,e):o],f=s.length,d=new Array(f*2);let h=0;for(let p=0;p<f;p++)d[h++]=(c-1)*a[p]/2+s[p],d[h++]=(u-1)*l/2+r[p];return d}}initializeState(){this.state={styleVersion:0,fontAtlasManager:new Mu},this.props.maxWidth>0&&T.once(1,"v8.9 breaking change: TextLayer maxWidth is now relative to text size")()}updateState(t){const{props:e,oldProps:i,changeFlags:o}=t;(o.dataChanged||o.updateTriggersChanged&&(o.updateTriggersChanged.all||o.updateTriggersChanged.getText))&&this._updateText(),(this._updateFontAtlas()||e.lineHeight!==i.lineHeight||e.wordBreak!==i.wordBreak||e.maxWidth!==i.maxWidth)&&this.setState({styleVersion:this.state.styleVersion+1})}getPickingInfo({info:t}){return t.object=t.index>=0?this.props.data[t.index]:null,t}_updateFontAtlas(){const{fontSettings:t,fontFamily:e,fontWeight:i,_getFontRenderer:o}=this.props,{fontAtlasManager:s,characterSet:r}=this.state,a={...t,characterSet:r,fontFamily:e,fontWeight:i,_getFontRenderer:o};if(!s.mapping)return s.setProps(a),!0;for(const l in a)if(a[l]!==s.props[l])return s.setProps(a),!0;return!1}_updateText(){var l;const{data:t,characterSet:e}=this.props,i=(l=t.attributes)==null?void 0:l.getText;let{getText:o}=this.props,s=t.startIndices,r;const a=e==="auto"&&new Set;if(i&&s){const{texts:c,characterCount:u}=Au({...ArrayBuffer.isView(i)?{value:i}:i,length:t.length,startIndices:s,characterSet:a});r=u,o=(f,{index:d})=>c[d]}else{const{iterable:c,objectInfo:u}=ct(t);s=[0],r=0;for(const f of c){u.index++;const d=Array.from(o(f,u)||"");a&&d.forEach(a.add,a),r+=d.length,s.push(r)}}this.setState({getText:o,startIndices:s,numInstances:r,characterSet:a||e})}transformParagraph(t,e){const{fontAtlasManager:i}=this.state,o=i.mapping,{baselineOffset:s}=i.atlas,{fontSize:r}=i.props,a=this.state.getText,{wordBreak:l,lineHeight:c,maxWidth:u}=this.props,f=a(t,e)||"";return wu(f,s,c*r,l,u*r,o)}renderLayers(){const{startIndices:t,numInstances:e,getText:i,fontAtlasManager:{atlas:o,mapping:s},styleVersion:r}=this.state,{data:a,_dataDiff:l,getPosition:c,getColor:u,getSize:f,getAngle:d,getPixelOffset:h,getBackgroundColor:p,getBorderColor:g,getBorderWidth:m,getContentBox:x,backgroundBorderRadius:b,backgroundPadding:v,background:_,billboard:C,fontSettings:w,outlineWidth:I,outlineColor:O,sizeScale:L,sizeUnits:E,sizeMinPixels:F,sizeMaxPixels:U,contentCutoffPixels:K,contentAlignHorizontal:ut,contentAlignVertical:Tt,transitions:M,updateTriggers:S}=this.props,Fo=this.getSubLayerClass("characters",si),ko=this.getSubLayerClass("background",ai),{fontSize:ci}=this.state.fontAtlasManager.props;return[_&&new ko({getFillColor:p,getLineColor:g,getLineWidth:m,borderRadius:b,padding:v,getPosition:c,getSize:f,getAngle:d,getPixelOffset:h,getClipRect:x,billboard:C,sizeScale:L,sizeUnits:E,sizeMinPixels:F,sizeMaxPixels:U,fontSize:ci,transitions:M&&{getPosition:M.getPosition,getAngle:M.getAngle,getSize:M.getSize,getFillColor:M.getBackgroundColor,getLineColor:M.getBorderColor,getLineWidth:M.getBorderWidth,getPixelOffset:M.getPixelOffset}},this.getSubLayerProps({id:"background",updateTriggers:{getPosition:S.getPosition,getAngle:S.getAngle,getSize:S.getSize,getFillColor:S.getBackgroundColor,getLineColor:S.getBorderColor,getLineWidth:S.getBorderWidth,getPixelOffset:S.getPixelOffset,getBoundingRect:{getText:S.getText,getTextAnchor:S.getTextAnchor,getAlignmentBaseline:S.getAlignmentBaseline,styleVersion:r}}}),{data:a.attributes&&a.attributes.background?{length:a.length,attributes:a.attributes.background}:a,_dataDiff:l,autoHighlight:!1,getBoundingRect:this.getBoundingRect}),new Fo({sdf:w.sdf,smoothing:Number.isFinite(w.smoothing)?w.smoothing:at.smoothing,outlineWidth:I/(w.radius||at.radius),outlineColor:O,iconAtlas:o,iconMapping:s,getPosition:c,getColor:u,getSize:f,getAngle:d,getPixelOffset:h,getContentBox:x,billboard:C,sizeScale:L,sizeUnits:E,sizeMinPixels:F,sizeMaxPixels:U,fontSize:ci,contentCutoffPixels:K,contentAlignHorizontal:ut,contentAlignVertical:Tt,transitions:M&&{getPosition:M.getPosition,getAngle:M.getAngle,getColor:M.getColor,getSize:M.getSize,getPixelOffset:M.getPixelOffset,getContentBox:M.getContentBox}},this.getSubLayerProps({id:"characters",updateTriggers:{all:S.getText,getPosition:S.getPosition,getAngle:S.getAngle,getColor:S.getColor,getSize:S.getSize,getPixelOffset:S.getPixelOffset,getContentBox:S.getContentBox,getIconOffsets:{getTextAnchor:S.getTextAnchor,getAlignmentBaseline:S.getAlignmentBaseline,styleVersion:r}}}),{data:a,_dataDiff:l,startIndices:t,numInstances:e,getIconOffsets:this.getIconOffsets,getIcon:i})]}static set fontAtlasCacheLimit(t){Ou(t)}}li.defaultProps=Uu;li.layerName="TextLayer";const Vt={circle:{type:ti,props:{filled:"filled",stroked:"stroked",lineWidthMaxPixels:"lineWidthMaxPixels",lineWidthMinPixels:"lineWidthMinPixels",lineWidthScale:"lineWidthScale",lineWidthUnits:"lineWidthUnits",pointRadiusMaxPixels:"radiusMaxPixels",pointRadiusMinPixels:"radiusMinPixels",pointRadiusScale:"radiusScale",pointRadiusUnits:"radiusUnits",pointAntialiasing:"antialiasing",pointBillboard:"billboard",getFillColor:"getFillColor",getLineColor:"getLineColor",getLineWidth:"getLineWidth",getPointRadius:"getRadius"}},icon:{type:fe,props:{iconAtlas:"iconAtlas",iconMapping:"iconMapping",iconSizeMaxPixels:"sizeMaxPixels",iconSizeMinPixels:"sizeMinPixels",iconSizeScale:"sizeScale",iconSizeUnits:"sizeUnits",iconAlphaCutoff:"alphaCutoff",iconBillboard:"billboard",getIcon:"getIcon",getIconAngle:"getAngle",getIconColor:"getColor",getIconPixelOffset:"getPixelOffset",getIconSize:"getSize"}},text:{type:li,props:{textSizeMaxPixels:"sizeMaxPixels",textSizeMinPixels:"sizeMinPixels",textSizeScale:"sizeScale",textSizeUnits:"sizeUnits",textBackground:"background",textBackgroundPadding:"backgroundPadding",textFontFamily:"fontFamily",textFontWeight:"fontWeight",textLineHeight:"lineHeight",textMaxWidth:"maxWidth",textOutlineColor:"outlineColor",textOutlineWidth:"outlineWidth",textWordBreak:"wordBreak",textCharacterSet:"characterSet",textBillboard:"billboard",textFontSettings:"fontSettings",getText:"getText",getTextAngle:"getAngle",getTextColor:"getColor",getTextPixelOffset:"getPixelOffset",getTextSize:"getSize",getTextAnchor:"getTextAnchor",getTextAlignmentBaseline:"getAlignmentBaseline",getTextBackgroundColor:"getBackgroundColor",getTextBorderColor:"getBorderColor",getTextBorderWidth:"getBorderWidth"}}},Wt={type:de,props:{lineWidthUnits:"widthUnits",lineWidthScale:"widthScale",lineWidthMinPixels:"widthMinPixels",lineWidthMaxPixels:"widthMaxPixels",lineJointRounded:"jointRounded",lineCapRounded:"capRounded",lineMiterLimit:"miterLimit",lineBillboard:"billboard",getLineColor:"getColor",getLineWidth:"getWidth"}},qe={type:ge,props:{extruded:"extruded",filled:"filled",wireframe:"wireframe",elevationScale:"elevationScale",material:"material",_full3d:"_full3d",getElevation:"getElevation",getFillColor:"getFillColor",getLineColor:"getLineColor"}};function pt({type:n,props:t}){const e={};for(const i in t)e[i]=n.defaultProps[t[i]];return e}function Ee(n,t){const{transitions:e,updateTriggers:i}=n.props,o={updateTriggers:{},transitions:e&&{getPosition:e.geometry}};for(const s in t){const r=t[s];let a=n.props[s];s.startsWith("get")&&(a=n.getSubLayerAccessor(a),o.updateTriggers[r]=i[s],e&&(o.transitions[r]=e[s])),o[r]=a}return o}function Du(n){if(Array.isArray(n))return n;switch(T.assert(n.type,"GeoJSON does not have type"),n.type){case"Feature":return[n];case"FeatureCollection":return T.assert(Array.isArray(n.features),"GeoJSON does not have features array"),n.features;default:return[{geometry:n}]}}function yn(n,t,e={}){const i={pointFeatures:[],lineFeatures:[],polygonFeatures:[],polygonOutlineFeatures:[]},{startRow:o=0,endRow:s=n.length}=e;for(let r=o;r<s;r++){const a=n[r],{geometry:l}=a;if(l)if(l.type==="GeometryCollection"){T.assert(Array.isArray(l.geometries),"GeoJSON does not have geometries array");const{geometries:c}=l;for(let u=0;u<c.length;u++){const f=c[u];vn(f,i,t,a,r)}}else vn(l,i,t,a,r)}return i}function vn(n,t,e,i,o){const{type:s,coordinates:r}=n,{pointFeatures:a,lineFeatures:l,polygonFeatures:c,polygonOutlineFeatures:u}=t;if(!Gu(s,r)){T.warn(`${s} coordinates are malformed`)();return}switch(s){case"Point":a.push(e({geometry:n},i,o));break;case"MultiPoint":r.forEach(f=>{a.push(e({geometry:{type:"Point",coordinates:f}},i,o))});break;case"LineString":l.push(e({geometry:n},i,o));break;case"MultiLineString":r.forEach(f=>{l.push(e({geometry:{type:"LineString",coordinates:f}},i,o))});break;case"Polygon":c.push(e({geometry:n},i,o)),r.forEach(f=>{u.push(e({geometry:{type:"LineString",coordinates:f}},i,o))});break;case"MultiPolygon":r.forEach(f=>{c.push(e({geometry:{type:"Polygon",coordinates:f}},i,o)),f.forEach(d=>{u.push(e({geometry:{type:"LineString",coordinates:d}},i,o))})});break}}const ju={Point:1,MultiPoint:2,LineString:2,MultiLineString:3,Polygon:3,MultiPolygon:4};function Gu(n,t){let e=ju[n];for(T.assert(e,`Unknown GeoJSON type ${n}`);t&&--e>0;)t=t[0];return t&&Number.isFinite(t[0])}function Ro(){return{points:{},lines:{},polygons:{},polygonsOutline:{}}}function Nt(n){return n.geometry.coordinates}function $u(n,t){const e=Ro(),{pointFeatures:i,lineFeatures:o,polygonFeatures:s,polygonOutlineFeatures:r}=n;return e.points.data=i,e.points._dataDiff=t.pointFeatures&&(()=>t.pointFeatures),e.points.getPosition=Nt,e.lines.data=o,e.lines._dataDiff=t.lineFeatures&&(()=>t.lineFeatures),e.lines.getPath=Nt,e.polygons.data=s,e.polygons._dataDiff=t.polygonFeatures&&(()=>t.polygonFeatures),e.polygons.getPolygon=Nt,e.polygonsOutline.data=r,e.polygonsOutline._dataDiff=t.polygonOutlineFeatures&&(()=>t.polygonOutlineFeatures),e.polygonsOutline.getPath=Nt,e}function Vu(n,t){const e=Ro(),{points:i,lines:o,polygons:s}=n,r=fu(n,t);e.points.data={length:i.positions.value.length/i.positions.size,attributes:{...i.attributes,getPosition:i.positions,instancePickingColors:{size:4,value:r.points}},properties:i.properties,numericProps:i.numericProps,featureIds:i.featureIds},e.lines.data={length:o.pathIndices.value.length-1,startIndices:o.pathIndices.value,attributes:{...o.attributes,getPath:o.positions,instancePickingColors:{size:4,value:r.lines}},properties:o.properties,numericProps:o.numericProps,featureIds:o.featureIds},e.lines._pathType="open";const a=s.positions.value.length/s.positions.size,l=Array(a).fill(1);for(const c of s.primitivePolygonIndices.value)l[c-1]=0;return e.polygons.data={length:s.polygonIndices.value.length-1,startIndices:s.polygonIndices.value,attributes:{...s.attributes,getPolygon:s.positions,instanceVertexValid:{size:1,value:new Uint16Array(l)},pickingColors:{size:4,value:r.polygons}},properties:s.properties,numericProps:s.numericProps,featureIds:s.featureIds},e.polygons._normalize=!1,s.triangles&&(e.polygons.data.attributes.indices=s.triangles.value),e.polygonsOutline.data={length:s.primitivePolygonIndices.value.length-1,startIndices:s.primitivePolygonIndices.value,attributes:{...s.attributes,getPath:s.positions,instancePickingColors:{size:4,value:r.polygons}},properties:s.properties,numericProps:s.numericProps,featureIds:s.featureIds},e.polygonsOutline._pathType="open",e}const Wu=["points","linestrings","polygons"],Hu={...pt(Vt.circle),...pt(Vt.icon),...pt(Vt.text),...pt(Wt),...pt(qe),stroked:!0,filled:!0,extruded:!1,wireframe:!1,_full3d:!1,iconAtlas:{type:"object",value:null},iconMapping:{type:"object",value:{}},getIcon:{type:"accessor",value:n=>n.properties.icon},getText:{type:"accessor",value:n=>n.properties.text},pointType:"circle",getRadius:{deprecatedFor:"getPointRadius"}};class zo extends ue{initializeState(){this.state={layerProps:{},features:{},featuresDiff:{}}}updateState({props:t,changeFlags:e}){if(!e.dataChanged)return;const{data:i}=this.props,o=i&&"points"in i&&"polygons"in i&&"lines"in i;this.setState({binary:o}),o?this._updateStateBinary({props:t,changeFlags:e}):this._updateStateJSON({props:t,changeFlags:e})}_updateStateBinary({props:t,changeFlags:e}){const i=Vu(t.data,this.encodePickingColor);this.setState({layerProps:i})}_updateStateJSON({props:t,changeFlags:e}){const i=Du(t.data),o=this.getSubLayerRow.bind(this);let s={};const r={};if(Array.isArray(e.dataChanged)){const l=this.state.features;for(const c in l)s[c]=l[c].slice(),r[c]=[];for(const c of e.dataChanged){const u=yn(i,o,c);for(const f in l)r[f].push(wo({data:s[f],getIndex:d=>d.__source.index,dataRange:c,replace:u[f]}))}}else s=yn(i,o);const a=$u(s,r);this.setState({features:s,featuresDiff:r,layerProps:a})}getPickingInfo(t){const e=super.getPickingInfo(t),{index:i,sourceLayer:o}=e;return e.featureType=Wu.find(s=>o.id.startsWith(`${this.id}-${s}-`)),i>=0&&o.id.startsWith(`${this.id}-points-text`)&&this.state.binary&&(e.index=this.props.data.points.globalFeatureIds.value[i]),e}_updateAutoHighlight(t){const e=`${this.id}-points-`,i=t.featureType==="points";for(const o of this.getSubLayers())o.id.startsWith(e)===i&&o.updateAutoHighlight(t)}_renderPolygonLayer(){var r;const{extruded:t,wireframe:e}=this.props,{layerProps:i}=this.state,o="polygons-fill",s=this.shouldRenderSubLayer(o,(r=i.polygons)==null?void 0:r.data)&&this.getSubLayerClass(o,qe.type);if(s){const a=Ee(this,qe.props),l=t&&e;return l||delete a.getLineColor,a.updateTriggers.lineColors=l,new s(a,this.getSubLayerProps({id:o,updateTriggers:a.updateTriggers}),i.polygons)}return null}_renderLineLayers(){var l,c;const{extruded:t,stroked:e}=this.props,{layerProps:i}=this.state,o="polygons-stroke",s="linestrings",r=!t&&e&&this.shouldRenderSubLayer(o,(l=i.polygonsOutline)==null?void 0:l.data)&&this.getSubLayerClass(o,Wt.type),a=this.shouldRenderSubLayer(s,(c=i.lines)==null?void 0:c.data)&&this.getSubLayerClass(s,Wt.type);if(r||a){const u=Ee(this,Wt.props);return[r&&new r(u,this.getSubLayerProps({id:o,updateTriggers:u.updateTriggers}),i.polygonsOutline),a&&new a(u,this.getSubLayerProps({id:s,updateTriggers:u.updateTriggers}),i.lines)]}return null}_renderPointLayers(){var a;const{pointType:t}=this.props,{layerProps:e,binary:i}=this.state;let{highlightedObjectIndex:o}=this.props;!i&&Number.isFinite(o)&&(o=e.points.data.findIndex(l=>l.__source.index===o));const s=new Set(t.split("+")),r=[];for(const l of s){const c=`points-${l}`,u=Vt[l],f=u&&this.shouldRenderSubLayer(c,(a=e.points)==null?void 0:a.data)&&this.getSubLayerClass(c,u.type);if(f){const d=Ee(this,u.props);let h=e.points;if(l==="text"&&i){const{instancePickingColors:p,...g}=h.data.attributes;h={...h,data:{...h.data,attributes:g}}}r.push(new f(d,this.getSubLayerProps({id:c,updateTriggers:d.updateTriggers,highlightedObjectIndex:o}),h))}}return r}renderLayers(){const{extruded:t}=this.props,e=this._renderPolygonLayer(),i=this._renderLineLayers(),o=this._renderPointLayers();return[!t&&e,i,o,t&&e]}getSubLayerAccessor(t){const{binary:e}=this.state;return!e||typeof t!="function"?super.getSubLayerAccessor(t):(i,o)=>{const{data:s,index:r}=o,a=cu(s,r);return t(a,o)}}}zo.layerName="GeoJsonLayer";zo.defaultProps=Hu;export{oo as ArcLayer,so as BitmapLayer,ni as ColumnLayer,zo as GeoJsonLayer,vo as GridCellLayer,fe as IconLayer,lo as LineLayer,de as PathLayer,fo as PointCloudLayer,So as PolygonLayer,ti as ScatterplotLayer,ge as SolidPolygonLayer,li as TextLayer,si as _MultiIconLayer,ai as _TextBackgroundLayer};
