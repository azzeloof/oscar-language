#include <pybind11/pybind11.h>
#include <pybind11/stl.h>
#include <pybind11/numpy.h>
#include <portaudio.h>
#include <iostream>
#include <vector>
#include <string>
#include <cmath>
#include <atomic>
#include <memory>
#include <algorithm>
#include <mutex>
#include <map>

#ifndef M_PI
#define M_PI 3.14159265358979323846
#endif

namespace py = pybind11;

// --- Structs and helper functions should be defined before use ---

struct DeviceInfo {
    int index;
    std::string name;
    int maxOutputChannels;
};

void pa_check_error(PaError err, const std::string& message) {
    if (err != paNoError) {
        throw std::runtime_error(message + ": " + Pa_GetErrorText(err));
    }
}

void initialize() {
    pa_check_error(Pa_Initialize(), "Failed to initialize PortAudio");
    py::print("PortAudio initialized.");
}

void terminate() {
    Pa_Terminate();
    py::print("PortAudio terminated.");
}

std::vector<DeviceInfo> getDeviceDetails() {
    std::vector<DeviceInfo> deviceDetails;
    int numDevices = Pa_GetDeviceCount();
    if (numDevices < 0) pa_check_error(numDevices, "Failed to get device count");
    for (int i = 0; i < numDevices; ++i) {
        const PaDeviceInfo* deviceInfo = Pa_GetDeviceInfo(i);
        if (deviceInfo) {
            // This line now works because DeviceInfo is a complete type
            deviceDetails.push_back({i, std::string(deviceInfo->name), deviceInfo->maxOutputChannels});
        }
    }
    return deviceDetails;
}


class Synth : public std::enable_shared_from_this<Synth> {
private:
    std::atomic<bool> is_playing_{false};
    std::atomic<double> phase_offset_{0.f};
    double sample_rate_;
    std::atomic<double> amplitude_{0.5f};
    std::atomic<double> frequency_{440.f};
    std::vector<float> wavetable_;
    mutable std::mutex wavetable_mutex_;

public:
    Synth(double sample_rate, std::vector<float> table) : 
        sample_rate_(sample_rate),
        wavetable_(std::move(table))
    {   
        if (wavetable_.empty()) {
            wavetable_.push_back(0.f);
        }
    }
    virtual ~Synth() = default;

    Synth(const Synth&) = delete;
    Synth& operator=(const Synth&) = delete;

    void render(float* mono_out, unsigned long frames, double master_phase_start) {
        std::lock_guard<std::mutex> lock(wavetable_mutex_);
        if (wavetable_.empty()) return;
        double table_size = static_cast<double>(wavetable_.size());
        double current_master_phase = master_phase_start;
        double freq = frequency_.load();
        double amp = amplitude_.load();
        double sample_offset = phase_offset_.load() * table_size;
        for (unsigned long i=0; i<frames; ++i) {
            double total_cycles = (current_master_phase * freq) / this->sample_rate_;
            double phase_with_offset = (total_cycles * table_size) + sample_offset;
            double phase_wrapped = fmod(phase_with_offset, table_size);
            if (phase_wrapped < 0) phase_wrapped += table_size;
            unsigned int i0 = static_cast<unsigned int>(phase_wrapped);
            unsigned int i1 = (i0 + 1) % wavetable_.size();
            double frac = phase_wrapped - i0;
            float val0 = wavetable_[i0];
            float val1 = wavetable_[i1];
            float current_sample = static_cast<float>(val0 + frac * (val1 - val0));
            mono_out[i] = current_sample * amp;
            current_master_phase += 1.f;
        }
    }

    void start() { is_playing_.store(true); }
    void stop() { is_playing_.store(false); }
    bool is_playing() const { return is_playing_.load(); }
    void set_frequency(double freq) { this->frequency_.store(freq); }
    double get_frequency() const { return frequency_; }
    void set_amplitude(double amp) { this->amplitude_.store(amp); }
    double get_amplitude() const { return amplitude_; }
    void update_wavetable(std::vector<float> new_table) {
        if (new_table.empty()) return;
        std::lock_guard<std::mutex> lock(wavetable_mutex_);
        wavetable_ = std::move(new_table);
    }
    void set_phase_offset(double offset) { this->phase_offset_.store(offset); }
    double get_phase_offset() const { return phase_offset_.load(); }
};


class Patch : public std::enable_shared_from_this<Patch> {
private:
    std::string synth_name_;
    std::vector<int> channels_;

public:
    Patch(std::string synth_name, std::vector<int> channels) 
        : synth_name_(std::move(synth_name)), channels_(std::move(channels)) {}
    ~Patch() = default;

    const std::string& get_synth_name() const { return synth_name_; }
    const std::vector<int>& get_channels() const { return channels_; }
    void set_synth_name(const std::string& name) { synth_name_ = name; }
    void set_channels(const std::vector<int>& channels) { channels_ = channels; }
};


class AudioEngine {
private:
    PaStream* stream_{nullptr};
    double sample_rate_;
    int numOutputChannels_{0};
    std::atomic<float> master_volume{1.f};
    std::atomic<double> master_phase_{0.f};
    
    std::map<std::string, std::shared_ptr<Synth>> synths_;
    std::map<std::string, std::shared_ptr<Patch>> patches_;
    
    std::recursive_mutex engine_mutex_;
    std::vector<std::string> synth_names_to_delete_;
    std::vector<std::string> patch_names_to_delete_;

    void _cleanup() {
        std::lock_guard<std::recursive_mutex> lock(engine_mutex_);
        if (synth_names_to_delete_.empty() && patch_names_to_delete_.empty()) return;

        for (const auto& name : patch_names_to_delete_) {
            patches_.erase(name);
        }
        patch_names_to_delete_.clear();

        for (const auto& name : synth_names_to_delete_) {
            synths_.erase(name);
        }
        synth_names_to_delete_.clear();
    }

    int paCallback(const void* inputBuffer, void* outputBuffer,
                   unsigned long framesPerBuffer,
                   const PaStreamCallbackTimeInfo* timeInfo,
                   PaStreamCallbackFlags statusFlags) {
        
        _cleanup();

        auto* out = static_cast<float*>(outputBuffer);
        std::fill_n(out, framesPerBuffer * this->numOutputChannels_, 0.0f);
        
        std::vector<float> mono_buffer(framesPerBuffer);
        
        double current_master_phase = master_phase_.load();
        float current_master_volume = master_volume.load();

        std::lock_guard<std::recursive_mutex> lock(engine_mutex_);
        
        for (const auto& [patch_name, patch_ptr] : patches_) {
            auto synth_it = synths_.find(patch_ptr->get_synth_name());
            if (synth_it != synths_.end() && synth_it->second->is_playing()) {
                std::shared_ptr<Synth> synth = synth_it->second;
                synth->render(mono_buffer.data(), framesPerBuffer, current_master_phase);
                
                for (int channel_index : patch_ptr->get_channels()) {
                    if (channel_index < this->numOutputChannels_) {
                        for (unsigned long frame = 0; frame < framesPerBuffer; ++frame) {
                            out[frame * this->numOutputChannels_ + channel_index] += mono_buffer[frame] * current_master_volume;
                        }
                    }
                }
            }
        }
        master_phase_.store(current_master_phase + framesPerBuffer);
        return paContinue;
    }

    static int paCallbackAdapter(const void* inputBuffer, void* outputBuffer,
                                 unsigned long framesPerBuffer,
                                 const PaStreamCallbackTimeInfo* timeInfo,
                                 PaStreamCallbackFlags statusFlags,
                                 void* userData) {
        return static_cast<AudioEngine*>(userData)->paCallback(inputBuffer, outputBuffer, framesPerBuffer, timeInfo, statusFlags);
    }

public:
    AudioEngine(int deviceIndex, int numChannels) : numOutputChannels_(numChannels) {
        const PaDeviceInfo* deviceInfo = Pa_GetDeviceInfo(deviceIndex);
        if (deviceInfo == nullptr) throw std::runtime_error("Invalid device index");
        if (numChannels > deviceInfo->maxOutputChannels) {
            throw std::runtime_error("Device does not support requested number of output channels");
        }
        
        this->sample_rate_ = deviceInfo->defaultSampleRate;
        py::print("Device reports default sample rate of: ", this->sample_rate_);

        PaStreamParameters outputParameters;
        outputParameters.device = deviceIndex;
        outputParameters.channelCount = numChannels;
        outputParameters.sampleFormat = paFloat32;
        outputParameters.suggestedLatency = Pa_GetDeviceInfo(deviceIndex)->defaultLowOutputLatency;
        outputParameters.hostApiSpecificStreamInfo = nullptr;

        pa_check_error(
            Pa_OpenStream(&this->stream_, nullptr, &outputParameters, this->sample_rate_, 
                          paFramesPerBufferUnspecified, paNoFlag, paCallbackAdapter, this),
            "Failed to open PortAudio stream"
        );
        pa_check_error(Pa_StartStream(this->stream_), "Failed to start PortAudio stream");
        py::print("PortAudio stream started on '", deviceInfo->name, "' with ", numChannels, " channels.");
    }

    ~AudioEngine() {
        if (stream_) {
            Pa_StopStream(stream_);
            Pa_CloseStream(stream_);
        }
        py::print("AudioEngine instance destroyed. Stream stopped and closed.");
    }

    std::shared_ptr<Synth> get_or_create_synth(const std::string& name, py::array_t<float> table) {
        std::lock_guard<std::recursive_mutex> lock(engine_mutex_);
        auto it = synths_.find(name);
        if (it != synths_.end()) {
            std::vector<float> table_vec(table.data(), table.data() + table.size());
            it->second->update_wavetable(std::move(table_vec));
            py::print("Synth '", name, "' already exists. Wavetable updated.");
            return it->second;
        } else {
            py::print("Creating new wavetable synth with name: '", name, "'");
            std::vector<float> table_vec(table.data(), table.data() + table.size());
            auto new_synth = std::make_shared<Synth>(this->sample_rate_, std::move(table_vec));
            synths_[name] = new_synth;
            return new_synth;
        }
    }

    std::shared_ptr<Patch> get_or_create_patch(const std::string& patch_name, const std::string& synth_name, std::vector<int> channels) {
        std::lock_guard<std::recursive_mutex> lock(engine_mutex_);
        if (synths_.find(synth_name) == synths_.end()) {
            throw std::runtime_error("Cannot create patch: synth with name '" + synth_name + "' does not exist.");
        }

        auto it = patches_.find(patch_name);
        if (it != patches_.end()) {
            it->second->set_synth_name(synth_name);
            it->second->set_channels(channels);
            return it->second;
        } else {
            auto new_patch = std::make_shared<Patch>(synth_name, channels);
            patches_[patch_name] = new_patch;
            return new_patch;
        }
    }

    void delete_synth(const std::string& name) {
        std::lock_guard<std::recursive_mutex> lock(engine_mutex_);
        if (synths_.find(name) == synths_.end()) return;

        // Add the synth to the deletion queue
        synth_names_to_delete_.push_back(name);

        // Add all associated patches to the deletion queue
        for (auto const& [patch_name, patch_ptr] : patches_) {
            if (patch_ptr->get_synth_name() == name) {
                patch_names_to_delete_.push_back(patch_name);
            }
        }
    }

    void delete_patch(const std::string& name) {
        std::lock_guard<std::recursive_mutex> lock(engine_mutex_);
        if (patches_.find(name) == patches_.end()) return;
        patch_names_to_delete_.push_back(name);
    }

    std::vector<std::string> list_synths() {
        std::lock_guard<std::recursive_mutex> lock(engine_mutex_);
        std::vector<std::string> names;
        for (const auto& [name, synth_ptr] : synths_) {
            names.push_back(name);
        }
        return names;
    }

    std::vector<std::string> list_patches() {
        std::lock_guard<std::recursive_mutex> lock(engine_mutex_);
        std::vector<std::string> names;
        for (const auto& [name, patch_ptr] : patches_) {
            names.push_back(name);
        }
        return names;
    }

    void set_master_volume(float volume) {
        std::lock_guard<std::recursive_mutex> lock(engine_mutex_);
        master_volume = volume;
    }

    float get_master_volume() {
        std::lock_guard<std::recursive_mutex> lock(engine_mutex_);
        return master_volume;
    }

    void stop_all() {
        std::lock_guard<std::recursive_mutex> lock(engine_mutex_);
        for (const auto& [name, synth_ptr] : synths_) {
            synth_ptr->stop();
        }
    }
};


PYBIND11_MODULE(oscar_server, m) {
    m.doc() = "A live-coding audio engine with named synths and patches";
    
    m.def("initialize", &initialize, "Initializes the PortAudio library. Must be called first.");
    m.def("terminate", &terminate, "Terminates the PortAudio library. Must be called last.");
    m.def("get_device_details", &getDeviceDetails, "Gets a list of all available audio devices.");

    py::class_<DeviceInfo>(m, "DeviceInfo")
        .def_readonly("index", &DeviceInfo::index)
        .def_readonly("name", &DeviceInfo::name)
        .def_readonly("max_output_channels", &DeviceInfo::maxOutputChannels)
        .def("__repr__", [](const DeviceInfo &d) {
            return "<DeviceInfo " + std::to_string(d.index) + ": '" + d.name + "' ("
                   + std::to_string(d.maxOutputChannels) + " channels)>";
        });

    py::class_<Synth, std::shared_ptr<Synth>>(m, "Synth")
        .def("start", &Synth::start)
        .def("stop", &Synth::stop)
        .def("is_playing", &Synth::is_playing)
        .def("set_frequency", &Synth::set_frequency)
        .def("get_frequency", &Synth::get_frequency)
        .def("set_amplitude", &Synth::set_amplitude)
        .def("get_amplitude", &Synth::get_amplitude)
        .def("update_wavetable", &Synth::update_wavetable)
        .def("set_phase_offset", &Synth::set_phase_offset)
        .def("get_phase_offset", &Synth::get_phase_offset);
    
    py::class_<Patch, std::shared_ptr<Patch>>(m, "Patch")
        .def("get_channels", &Patch::get_channels)
        .def("get_synth_name", &Patch::get_synth_name)
        .def("set_synth_name", &Patch::set_synth_name)
        .def("set_channels", &Patch::set_channels);

    py::class_<AudioEngine>(m, "AudioEngine")
        .def(py::init<int, int>(), py::arg("device_index"), py::arg("num_channels"))
        .def("get_or_create_synth", &AudioEngine::get_or_create_synth, py::arg("name"), py::arg("wavetable"), "Gets or creates a synth by its unique name.")
        .def("get_or_create_patch", &AudioEngine::get_or_create_patch, py::arg("patch_name"), py::arg("synth_name"), py::arg("channels"), "Gets or creates a patch to route a synth to channels.")
        .def("delete_synth", &AudioEngine::delete_synth, py::arg("name"), "Schedules a named synth and its associated patches for deletion.")
        .def("delete_patch", &AudioEngine::delete_patch, py::arg("name"), "Schedules a named patch for deletion.")
        .def("list_synths", &AudioEngine::list_synths, "Lists all synths currently in use.")
        .def("list_patches", &AudioEngine::list_patches, "Lists all patches currently in use.")
        .def("set_master_volume", &AudioEngine::set_master_volume, py::arg("volume"), "Sets the master volume of the engine.")
        .def("get_master_volume", &AudioEngine::get_master_volume, "Gets the master volume of the engine.")
        .def("stop_all", &AudioEngine::stop_all, "Stops all synths in the engine.");
};
