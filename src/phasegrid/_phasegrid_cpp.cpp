#include <Python.h>
#include <cmath>
#include <limits>
#include <vector>

static double phase_distance(double left, double right) {
    constexpr double pi = 3.14159265358979323846;
    constexpr double tau = 2.0 * pi;
    double value = std::fmod(left - right + pi, tau);
    if (value < 0.0) {
        value += tau;
    }
    return value - pi;
}

static bool to_vector(PyObject* object, std::vector<double>& output) {
    PyObject* sequence = PySequence_Fast(object, "expected a sequence");
    if (!sequence) {
        return false;
    }
    Py_ssize_t size = PySequence_Fast_GET_SIZE(sequence);
    output.reserve(static_cast<size_t>(size));
    for (Py_ssize_t index = 0; index < size; ++index) {
        PyObject* item = PySequence_Fast_GET_ITEM(sequence, index);
        double value = PyFloat_AsDouble(item);
        if (PyErr_Occurred()) {
            Py_DECREF(sequence);
            return false;
        }
        output.push_back(value);
    }
    Py_DECREF(sequence);
    return true;
}

static PyObject* select_weighted(PyObject*, PyObject* args) {
    PyObject* target_obj;
    PyObject* phase_obj;
    PyObject* transmission_obj;
    double phase_weight;
    double transmission_weight;
    if (!PyArg_ParseTuple(args, "OOOdd", &target_obj, &phase_obj, &transmission_obj, &phase_weight, &transmission_weight)) {
        return nullptr;
    }

    std::vector<double> targets;
    std::vector<double> phases;
    std::vector<double> transmissions;
    if (!to_vector(target_obj, targets) || !to_vector(phase_obj, phases) || !to_vector(transmission_obj, transmissions)) {
        return nullptr;
    }
    if (phases.size() != transmissions.size()) {
        PyErr_SetString(PyExc_ValueError, "candidate phases and transmissions must have the same length");
        return nullptr;
    }

    PyObject* result = PyList_New(static_cast<Py_ssize_t>(targets.size()));
    for (size_t i = 0; i < targets.size(); ++i) {
        size_t best_index = 0;
        double best_loss = std::numeric_limits<double>::infinity();
        for (size_t j = 0; j < phases.size(); ++j) {
            double phase_error = phase_distance(targets[i], phases[j]);
            double transmission_loss = 1.0 - transmissions[j];
            double loss = phase_weight * phase_error * phase_error + transmission_weight * transmission_loss * transmission_loss;
            if (loss < best_loss) {
                best_loss = loss;
                best_index = j;
            }
        }
        PyList_SET_ITEM(result, static_cast<Py_ssize_t>(i), PyLong_FromSize_t(best_index));
    }
    return result;
}

static PyMethodDef methods[] = {
    {"select_weighted", select_weighted, METH_VARARGS, "Select best candidate indices for weighted phase/transmission loss."},
    {nullptr, nullptr, 0, nullptr}
};

static struct PyModuleDef module = {
    PyModuleDef_HEAD_INIT,
    "_phasegrid_cpp",
    "C++ acceleration backend for phasegrid.",
    -1,
    methods
};

PyMODINIT_FUNC PyInit__phasegrid_cpp(void) {
    return PyModule_Create(&module);
}

