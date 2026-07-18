#include <Python.h>
#include <cmath>
#include <limits>
#include <string>
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

static double multichannel_loss(
    const std::vector<double>& targets,
    const std::vector<double>& phases,
    const std::vector<double>& transmissions,
    const std::vector<double>& channel_weights,
    const std::vector<double>& transmission_weights,
    const std::vector<double>& pb_spins,
    size_t site_index,
    size_t candidate_index,
    size_t n_candidates,
    size_t n_channels,
    double phase_weight,
    const std::string& phase_mode,
    double pb_spin,
    double theta
) {
    double total = 0.0;
    for (size_t channel = 0; channel < n_channels; ++channel) {
        const double target = targets[site_index * n_channels + channel];
        const double dynamic_phase = phases[candidate_index * n_channels + channel];
        const double transmission = transmissions[candidate_index * n_channels + channel];
        const double pb_phase = 2.0 * pb_spins[channel] * pb_spin * theta;
        double realized = dynamic_phase;
        if (phase_mode == "pb") {
            realized = pb_phase;
        } else if (phase_mode == "hybrid") {
            realized = dynamic_phase + pb_phase;
        }
        const double error = phase_distance(target, realized);
        const double transmission_loss = 1.0 - transmission;
        total += channel_weights[channel] * phase_weight * error * error;
        total += transmission_weights[channel] * transmission_loss * transmission_loss;
    }
    return total;
}

static PyObject* select_multichannel(PyObject*, PyObject* args) {
    PyObject* target_obj;
    PyObject* phase_obj;
    PyObject* transmission_obj;
    PyObject* channel_weight_obj;
    PyObject* transmission_weight_obj;
    PyObject* pb_spin_obj;
    Py_ssize_t n_sites;
    Py_ssize_t n_candidates;
    Py_ssize_t n_channels;
    double phase_weight;
    const char* phase_mode_c;
    int rotation_steps;
    double global_pb_spin;
    if (!PyArg_ParseTuple(
            args,
            "OOOOOOnnndsid",
            &target_obj,
            &phase_obj,
            &transmission_obj,
            &channel_weight_obj,
            &transmission_weight_obj,
            &pb_spin_obj,
            &n_sites,
            &n_candidates,
            &n_channels,
            &phase_weight,
            &phase_mode_c,
            &rotation_steps,
            &global_pb_spin)) {
        return nullptr;
    }

    std::vector<double> targets;
    std::vector<double> phases;
    std::vector<double> transmissions;
    std::vector<double> channel_weights;
    std::vector<double> transmission_weights;
    std::vector<double> pb_spins;
    if (!to_vector(target_obj, targets) || !to_vector(phase_obj, phases) || !to_vector(transmission_obj, transmissions) ||
        !to_vector(channel_weight_obj, channel_weights) || !to_vector(transmission_weight_obj, transmission_weights) ||
        !to_vector(pb_spin_obj, pb_spins)) {
        return nullptr;
    }
    if (n_sites <= 0 || n_candidates <= 0 || n_channels <= 0) {
        PyErr_SetString(PyExc_ValueError, "n_sites, n_candidates, and n_channels must be positive");
        return nullptr;
    }
    const size_t sites = static_cast<size_t>(n_sites);
    const size_t candidates = static_cast<size_t>(n_candidates);
    const size_t channels = static_cast<size_t>(n_channels);
    if (targets.size() != sites * channels || phases.size() != candidates * channels || transmissions.size() != candidates * channels ||
        channel_weights.size() != channels || transmission_weights.size() != channels || pb_spins.size() != channels) {
        PyErr_SetString(PyExc_ValueError, "flattened input sizes do not match dimensions");
        return nullptr;
    }

    const std::string phase_mode(phase_mode_c);
    const bool use_rotation = phase_mode == "pb" || phase_mode == "hybrid";
    const int theta_count = use_rotation ? rotation_steps : 1;
    if (theta_count <= 0) {
        PyErr_SetString(PyExc_ValueError, "rotation_steps must be positive");
        return nullptr;
    }

    PyObject* result = PyList_New(static_cast<Py_ssize_t>(sites));
    constexpr double pi = 3.14159265358979323846;
    for (size_t site = 0; site < sites; ++site) {
        size_t best_candidate = 0;
        int best_rotation = use_rotation ? 0 : -1;
        double best_loss = std::numeric_limits<double>::infinity();
        for (size_t candidate = 0; candidate < candidates; ++candidate) {
            for (int rotation_index = 0; rotation_index < theta_count; ++rotation_index) {
                const double theta = use_rotation ? rotation_index * pi / rotation_steps : 0.0;
                const double loss = multichannel_loss(
                    targets,
                    phases,
                    transmissions,
                    channel_weights,
                    transmission_weights,
                    pb_spins,
                    site,
                    candidate,
                    candidates,
                    channels,
                    phase_weight,
                    phase_mode,
                    global_pb_spin,
                    theta);
                if (loss < best_loss) {
                    best_loss = loss;
                    best_candidate = candidate;
                    best_rotation = use_rotation ? rotation_index : -1;
                }
            }
        }
        PyObject* item = Py_BuildValue("(ni)", static_cast<Py_ssize_t>(best_candidate), best_rotation);
        if (!item) {
            Py_DECREF(result);
            return nullptr;
        }
        PyList_SET_ITEM(result, static_cast<Py_ssize_t>(site), item);
    }
    return result;
}

static PyMethodDef methods[] = {
    {"select_weighted", select_weighted, METH_VARARGS, "Select best candidate indices for weighted phase/transmission loss."},
    {"select_multichannel", select_multichannel, METH_VARARGS, "Select candidate and rotation indices for multichannel/PB loss."},
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
