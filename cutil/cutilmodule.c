// Copyright 2019 University of Freiburg, Chair of Algorithms and Data
// Structures
// Authors: Patrick Brosi <brosi@cs.uni-freiburg.de>

#define PY_SSIZE_T_CLEAN
#include <Python.h>

#define MIN3(a, b, c) \
  ((a) < (b) ? ((a) < (c) ? (a) : (c)) : ((b) < (c) ? (b) : (c)))
#define DEG_RAD (M_PI / 180.0)
#define RAD_DEG (180 / M_PI)
#define MAX(a, b) ((a) > (b) ? (a) : (b))
#define MIN(a, b) ((a) < (b) ? (a) : (b))


// https://en.wikibooks.org/wiki/Algorithm_Implementation/Strings/Levenshtein_distance#C
static int ed(const Py_UNICODE* s1, const Py_UNICODE* s2, int s1len,
              int s2len) {
  unsigned int x, y, lastdiag, olddiag;
  unsigned int column[s1len + 1];

  if (s1len == 0 && s2len == 0) return 0;

  for (y = 1; y <= s1len; y++) column[y] = y;

  for (x = 1; x <= s2len; x++) {
    column[0] = x;
    for (y = 1, lastdiag = x - 1; y <= s1len; y++) {
      olddiag = column[y];
      column[y] = MIN3(column[y] + 1, column[y - 1] + 1,
                       lastdiag + (s1[y - 1] == s2[x - 1] ? 0 : 1));
      lastdiag = olddiag;
    }
  }

  return (column[s1len]);
}

static int ped(const Py_UNICODE* s1, const Py_UNICODE* s2, int s1len,
               int s2len) {
  unsigned int x, y;
  unsigned int matrix[s2len + 1][s1len + 1];

  if (s1len == 0 && s2len == 0) return 0;

  matrix[0][0] = 0;
  for (x = 1; x <= s2len; x++) matrix[x][0] = matrix[x - 1][0] + 1;
  for (y = 1; y <= s1len; y++) matrix[0][y] = matrix[0][y - 1] + 1;
  for (x = 1; x <= s2len; x++)
    for (y = 1; y <= s1len; y++)
      matrix[x][y] =
          MIN3(matrix[x - 1][y] + 1, matrix[x][y - 1] + 1,
               matrix[x - 1][y - 1] + (s1[y - 1] == s2[x - 1] ? 0 : 1));

  unsigned int min = s1len;
  for (unsigned int i = 0; i <= s2len; i++) {
    if (matrix[i][s1len] < min) min = matrix[i][s1len];
  }

  return min;
}

static int sed(const Py_UNICODE* s1, const Py_UNICODE* s2, int s1len,
               int s2len) {
  unsigned int x, y;
  unsigned int matrix[s2len + 1][s1len + 1];

  if (s1len == 0 && s2len == 0) return 0;

  matrix[0][0] = 0;
  for (x = 1; x <= s2len; x++) matrix[x][0] = matrix[x - 1][0] + 1;
  for (y = 1; y <= s1len; y++) matrix[0][y] = matrix[0][y - 1] + 1;
  for (x = 1; x <= s2len; x++)
    for (y = 1; y <= s1len; y++)
      matrix[x][y] =
          MIN3(matrix[x - 1][y] + 1, matrix[x][y - 1] + 1,
               matrix[x - 1][y - 1] + (s1[s1len - y] == s2[s2len - x] ? 0 : 1));

  unsigned int min = s1len;
  for (unsigned int i = 0; i <= s2len; i++) {
    if (matrix[i][s1len] < min) min = matrix[i][s1len];
  }

  return min;
}

static double jaro(const Py_UNICODE* s1, const Py_UNICODE* s2, int s1len,
                   int s2len) {
  if (s1len == 0) return s2len == 0 ? 1.0 : 0.0;

  // max distance between two chars to be considered matching
  // floor() is ommitted due to integer division rules
  int match_distance = (int)MAX(s1len, s2len) / 2 - 1;

  // arrays of bools that signify if that char in the matching string has a
  // match
  int* s1_matches = calloc(s1len, sizeof(int));
  int* s2_matches = calloc(s2len, sizeof(int));

  // number of matches and transpositions
  double matches = 0.0;
  double transpositions = 0.0;

  // find the matches
  for (int i = 0; i < s1len; i++) {
    // start and end take into account the match distance
    int start = MAX(0, i - match_distance);
    int end = MIN(i + match_distance + 1, s2len);

    for (int k = start; k < end; k++) {
      // if str2 already has a match continue
      if (s2_matches[k]) continue;
      // if str1 and str2 are not
      if (s1[i] != s2[k]) continue;
      // otherwise assume there is a match
      s1_matches[i] = 1;
      s2_matches[k] = 1;
      matches++;
      break;
    }
  }

  // if there are no matches return 0
  if (matches == 0) {
    free(s1_matches);
    free(s2_matches);
    return 0.0;
  }

  // count transpositions
  int k = 0;
  for (int i = 0; i < s1len; i++) {
    // if there are no matches in str1 continue
    if (!s1_matches[i]) continue;
    // while there is no match in str2 increment k
    while (!s2_matches[k]) k++;
    // increment transpositions
    if (s1[i] != s2[k]) transpositions++;
    k++;
  }

  transpositions /= 2.0;

  free(s1_matches);
  free(s2_matches);

  return ((matches / s1len) + (matches / s2len) +
          ((matches - transpositions) / matches)) /
         3.0;
}

double haversine(double lat1, double lng1, double lat2, double lng2) {
  lat1 *= DEG_RAD;
  lng1 *= DEG_RAD;
  lat2 *= DEG_RAD;
  lng2 *= DEG_RAD;

  double a =
      sin((lat2 - lat1) / 2) * sin((lat2 - lat1) / 2) +
      cos(lat1) * cos(lat2) * sin((lng2 - lng1) / 2) * sin((lng2 - lng1) / 2);
  return 12742.0 * asin(sqrt(a));
}

double haversine_approx(double lat1, double lng1, double lat2, double lng2) {
  lat1 *= DEG_RAD;
  lng1 *= DEG_RAD;
  lat2 *= DEG_RAD;
  lng2 *= DEG_RAD;

  double x = (lng2 - lng1) * cos(0.5 * (lat2 + lat1));
  double y = lat2 - lat1;
  return 6371.0 * sqrt(x * x + y * y);
}

static PyObject* cutil_ped(PyObject* self, PyObject* args) {
  Py_UNICODE* str_a;
  Py_UNICODE* str_b;
  Py_ssize_t len_a, len_b;

  if (!PyArg_ParseTuple(args, "u#u#", &str_a, &len_a, &str_b, &len_b)) return 0;

  return PyLong_FromLong(ped(str_a, str_b, len_a, len_b));
}

static PyObject* cutil_sed(PyObject* self, PyObject* args) {
  Py_UNICODE* str_a;
  Py_UNICODE* str_b;
  Py_ssize_t len_a, len_b;

  if (!PyArg_ParseTuple(args, "u#u#", &str_a, &len_a, &str_b, &len_b)) return 0;

  return PyLong_FromLong(sed(str_a, str_b, len_a, len_b));
}

static PyObject* cutil_jaro(PyObject* self, PyObject* args) {
  Py_UNICODE* str_a;
  Py_UNICODE* str_b;
  Py_ssize_t len_a, len_b;

  if (!PyArg_ParseTuple(args, "u#u#", &str_a, &len_a, &str_b, &len_b)) return 0;

  return PyFloat_FromDouble(jaro(str_a, str_b, len_a, len_b));
}

static PyObject* cutil_ed(PyObject* self, PyObject* args) {
  Py_UNICODE* str_a;
  Py_UNICODE* str_b;
  Py_ssize_t len_a, len_b;

  if (!PyArg_ParseTuple(args, "u#u#", &str_a, &len_a, &str_b, &len_b)) return 0;
  return PyLong_FromLong(ed(str_a, str_b, len_a, len_b));
}

static PyObject* cutil_haversine(PyObject* self, PyObject* args) {
  double lat1, lng1, lat2, lng2;
  if (!PyArg_ParseTuple(args, "dddd", &lat1, &lng1, &lat2, &lng2)) return 0;
  return Py_BuildValue("d", haversine(lat1, lng1, lat2, lng2));
}

static PyObject* cutil_haversine_approx(PyObject* self, PyObject* args) {
  double lat1, lng1, lat2, lng2;
  if (!PyArg_ParseTuple(args, "dddd", &lat1, &lng1, &lat2, &lng2)) return 0;
  return Py_BuildValue("d", haversine_approx(lat1, lng1, lat2, lng2));
}

static PyMethodDef CutilMethods[] = {
    {"ed", cutil_ed, METH_VARARGS, "Compute the edit distance."},
    {"ped", cutil_ped, METH_VARARGS, "Compute the prefix edit distance."},
    {"sed", cutil_sed, METH_VARARGS, "Compute the suffix edit distance."},
    {"jaro", cutil_jaro, METH_VARARGS, "Compute the jaro similarity."},
    {"haversine", cutil_haversine, METH_VARARGS,
     "Compute the haversine distance between two points."},
    {"haversine_approx", cutil_haversine_approx, METH_VARARGS,
     "Compute the approx haversine distance between two points."},
    {NULL, NULL, 0, NULL}};

static struct PyModuleDef cutilmodule = {PyModuleDef_HEAD_INIT, "cutil", 0, -1,
                                         CutilMethods};

PyMODINIT_FUNC PyInit_cutil(void) { return PyModule_Create(&cutilmodule); }
